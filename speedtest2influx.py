import time
import json
import subprocess
import os

from influxdb import InfluxDBClient
from datetime import datetime

# InfluxDB Settings
DB_ADDRESS = os.environ.get('DB_ADDRESS', 'db_hostname.network')
DB_PORT = os.environ.get('DB_PORT', 8086)
DB_USER = os.environ.get('DB_USER', 'db_username')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'db_password')
DB_DATABASE = os.environ.get('DB_DATABASE', 'speedtest_db')
DB_RETRY_INVERVAL = int(os.environ.get('DB_RETRY_INVERVAL', 60)) # Time before retrying a failed data upload.

# Speedtest Settings
TEST_INTERVAL = int(os.environ.get('TEST_INTERVAL', 1800))  # Time between tests (in seconds).
TEST_FAIL_INTERVAL = int(os.environ.get('TEST_FAIL_INTERVAL', 60))  # Time before retrying a failed Speedtest (in seconds).

PRINT_DATA = os.environ.get('PRINT_DATA', "False") # Do you want to see the results in your logs? Type must be str. Will be converted to bool.

influxdb_client = InfluxDBClient(
    DB_ADDRESS, DB_PORT, DB_USER, DB_PASSWORD, None)

def str2bool(v):
  return v.lower() in ("yes", "true", "t", "1")

def logger(level, message):
    print(level, ":", datetime.now().strftime("%d/%m/%Y %H:%M:%S"), ":", message)

def init_db():
    try:
        databases = influxdb_client.get_list_database()
    except:
        logger("Error", "Unable to get list of databases")
        raise RuntimeError("No DB connection") from error
    else:
        if len(list(filter(lambda x: x['name'] == DB_DATABASE, databases))) == 0:
            influxdb_client.create_database(
                DB_DATABASE)  # Create if does not exist.
        else:
            influxdb_client.switch_database(DB_DATABASE)  # Switch to if does exist.



def tag_selection(data):
    tags = DB_TAGS
    if tags is None:
        return None
    # tag_switch takes in _data and attaches CLIoutput to more readable ids
    tag_switch = {
        'isp': data['isp'],
        'interface': data['interface']['name'],
        'internal_ip': data['interface']['internalIp'],
        'interface_mac': data['interface']['macAddr'],
        'vpn_enabled': (False if data['interface']['isVpn'] == 'false' else True),
        'external_ip': data['interface']['externalIp'],
        'server_id': data['server']['id'],
        'server_name': data['server']['name'],
        'server_location': data['server']['location'],
        'server_country': data['server']['country'],
        'server_host': data['server']['host'],
        'server_port': data['server']['port'],
        'server_ip': data['server']['ip'],
        'speedtest_id': data['result']['id'],
        'speedtest_url': data['result']['url']
    }
    
    options = {}
    tags = tags.split(',')
    for tag in tags:
        # split the tag string, strip and add selected tags to {options} with corresponding tag_switch data
        tag = tag.strip()
        options[tag] = tag_switch[tag]
    return options

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
    tags = tag_selection(data)
    if tags is None:
        return influx_data
    else:
        for measurement in influx_data:
            measurement['tags'] = tags
        return influx_data


def main():
    db_initialized = False
    
    while(db_initialized == False): 
        try:
            init_db()  # Setup the database if it does not already exist.
        except:
            logger("Error", "DB initialization error")
            time.sleep(int(DB_RETRY_INVERVAL))
        else:
            logger("Info", "DB initialization complete")
            db_initialized = True
        
    while True:  # Run a Speedtest and send the results to influxDB indefinitely.
        logger("Info", "Speedtest Started...")
        speedtest = subprocess.run(
            ["speedtest", "--accept-license", "--accept-gdpr", "-f", "json"], capture_output=True)

        if speedtest.returncode == 0:  # Speedtest was successful.
            data = format_for_influx(speedtest.stdout)
            logger("Info", "Speedtest successful")
            try:
                if influxdb_client.write_points(data) == True:
                   logger("Info", "Data written to DB successfully")
                   if str2bool(PRINT_DATA) == True:
                      logger("Info", data)
                   time.sleep(TEST_INTERVAL)
            except:
                logger("Error", "Data write to DB failed")
                time.sleep(TEST_FAIL_INTERVAL)
        else:  # Speedtest failed.
            logger("Error", "Speedtest failed")
            logger("Error", speedtest.stderr)
            logger("Info", speedtest.stdout)
            time.sleep(TEST_FAIL_INTERVAL)


if __name__ == '__main__':
    logger('Info', 'Speedtest CLI Data Logger to InfluxDB started')
    main()