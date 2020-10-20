import time
import json
import subprocess

from influxdb import InfluxDBClient

# InfluxDB Settings
DB_ADDRESS = 'db_hostname.network'
DB_PORT = 8086
DB_USER = 'db_username'
DB_PASSWORD = 'db_password'
DB_DATABASE = 'speedtest_db'
DB_RETRY_INVERVAL = 60 # Time before retrying a failed data upload.

# Speedtest Settings
TEST_INTERVAL = 1800  # Time between tests (in seconds).
TEST_FAIL_INTERVAL = 60  # Time before retrying a failed Speedtest (in seconds).

influxdb_client = InfluxDBClient(
    DB_ADDRESS, DB_PORT, DB_USER, DB_PASSWORD, None)


def init_db():
    try:
        databases = influxdb_client.get_list_database()
    except:
        print("Error: Unable to get list of databases")
        raise RuntimeError("No DB connection") from error
    else:
        if len(list(filter(lambda x: x['name'] == DB_DATABASE, databases))) == 0:
            influxdb_client.create_database(
                DB_DATABASE)  # Create if does not exist.
        else:
            influxdb_client.switch_database(DB_DATABASE)  # Switch to if does exist.


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
                'packetLoss': float(data['packetLoss'])
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
            print("Error: DB initialization error")
            time.sleep(DB_RETRY_INVERVAL)
        else:
            print("Info: DB initialization complete")
            db_initialized = True
        
        
    while (1):  # Run a Speedtest and send the results to influxDB indefinitely.
        speedtest = subprocess.run(
            ["speedtest", "--accept-license", "--accept-gdpr", "-f", "json"], capture_output=True)

        if speedtest.returncode == 0:  # Speedtest was successful.
            data = format_for_influx(speedtest.stdout)
            print("Info: Speedtest successful")
            try:
                if influxdb_client.write_points(data) == True:
                    print("Info: Data written to DB successfully")
                    time.sleep(TEST_INTERVAL)
            except:
                print("Error: Data write to DB failed")
                time.sleep(TEST_FAIL_INTERVAL)
        else:  # Speedtest failed.
            print("Error: Speedtest failed")
            print(speedtest.stderr)
            print(speedtest.stdout)
            time.sleep(TEST_FAIL_INTERVAL)


if __name__ == '__main__':
    print('Speedtest CLI Data Logger to InfluxDB')
    main()
