import os
import time
import json
import logging
import datetime
import subprocess

from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

# InfluxDB Settings
DB_BUCKET = os.environ.get('DB_BUCKET', 'speedtest_bucket')
DB_RETRY_INVERVAL = int(os.environ.get('DB_RETRY_INVERVAL', 60)) # Time before retrying a failed data upload.

# Speedtest Settings
TEST_INTERVAL = int(os.environ.get('TEST_INTERVAL', 1800))  # Time between tests (in seconds).
TEST_FAIL_INTERVAL = int(os.environ.get('TEST_FAIL_INTERVAL', 60))  # Time before retrying a failed Speedtest (in seconds).

LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

level = logging.getLevelName(LOG_LEVEL)
logging.basicConfig(level=level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__file__)

client_db = InfluxDBClient.from_env_properties()
write_api = client_db.write_api(write_options=SYNCHRONOUS)

def init_db():
    try:
        buckets_api = client_db.buckets_api()
        bucket = buckets_api.find_bucket_by_name(DB_BUCKET)
    except:
        log.error('Unable to get bucket api')
        raise RuntimeError('No DB connection') from error
    else:
        if bucket is None:
            buckets_api.create_bucket(
                bucket_name=DB_BUCKET,
                org=os.environ.get('INFLUXDB_V2_ORG'),
                description='Speedtest CLI Data Logger')


def format_for_influx(cliout):
    data = json.loads(cliout)
    # There is additional data in the speedtest-cli output but it is likely not necessary to store.
    influx_data = [
        {
            'measurement': 'ping',
            'time': data['timestamp'],
            'fields': {
                'jitter': float(data['ping']['jitter']),
                'latency': float(data['ping']['latency'])
            }
        },
        {
            'measurement': 'download',
            'time': data['timestamp'],
            'fields': {
                # Byte to Megabit
                'bandwidth': data['download']['bandwidth'] / 125000,
                'bytes': data['download']['bytes'],
                'elapsed': data['download']['elapsed']
            }
        },
        {
            'measurement': 'upload',
            'time': data['timestamp'],
            'fields': {
                # Byte to Megabit
                'bandwidth': data['upload']['bandwidth'] / 125000,
                'bytes': data['upload']['bytes'],
                'elapsed': data['upload']['elapsed']
            }
        },
        {
            'measurement': 'packetLoss',
            'time': data['timestamp'],
            'fields': {
                'packetLoss': float(data.get('packetLoss', 0.0))
            }
        }
    ]
    return influx_data


def main():
    db_initialized = False
    
    while(db_initialized == False): 
        try:
            init_db()  # Setup the database if it does not already exist.
        except:
            log.error('DB initialization error')
            time.sleep(int(DB_RETRY_INVERVAL))
        else:
            log.info('DB initialization complete')
            db_initialized = True
        
    while True:  # Run a Speedtest and send the results to influxDB indefinitely.
        speedtest = subprocess.run(
            ['speedtest', '--accept-license', '--accept-gdpr', '-f', 'json'],
            capture_output=True,
            text=True)

        if speedtest.returncode == 0:  # Speedtest was successful.
            data = format_for_influx(speedtest.stdout)
            log.info('Speedtest successful')
            try:
                write_api.write(bucket=DB_BUCKET, record=data)
                log.info('Data written to DB successfully')
                log.debug(data)
                time.sleep(TEST_INTERVAL)
            except:
                log.error('Data write to DB failed')
                time.sleep(TEST_FAIL_INTERVAL)
        else:  # Speedtest failed.
            log.error('Speedtest failed')
            log.error(speedtest.stderr)
            log.info(speedtest.stdout)
            time.sleep(TEST_FAIL_INTERVAL)


if __name__ == '__main__':
    log.info('Speedtest CLI Data Logger to InfluxDB started')
    main()