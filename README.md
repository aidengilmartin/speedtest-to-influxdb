# Speedtest to InfluxDB

This is a small Python script that will continuously run the Speedtest CLI application by Ookla, reformat the data output and forward it on to an InfluxDB database.

You may want to do this so that you can track your internet connections consistency over time. Using Grafana you can view and explore this data easily.

![Grafana Dashboard](https://i.imgur.com/8cUdMy7.png)

## Using the script

Adjust the InfluxDB connection settings at the top of `main.py` to fit your setup and then run with one of the options listed below.

Be aware that this script will automatically accept the license and GDPR statement so that it can run non-interactively. Make sure you agree with them before running.

### 1. No Container

1. [Install the Speedtest CLI application by Ookla.](https://www.speedtest.net/apps/cli)

    NOTE: The `speedtest-cli` package in distro repositories is an unofficial client. It will need to be uninstalled before installing the Ookla Speedtest CLI application with the directions on their website.

2. Install the InfluxDB client for library from Python.

    `pip3 install influxdb`

3. Run the script.

    `python3 ./speedtest2influx.py`

### 2. Run with Docker or Podman

1. Build the container.

    `docker build -t aidengilmartin/speedtest-influx ./`

2. Run the container.

    `docker run -d --name speedtest-influx aidengilmartin/speedtest-influx`

3. Run the full stack with docker-compose

    In the docker_env/ folder you can edit the environment variables of the docker container (see below, [grafana](https://grafana.com/docs/grafana/latest/installation/docker/) and [influx](https://hub.docker.com/_/influxdb)). 

    `docker-compose up -d`

    Login to the Grafana Dashboard (admin/admin) and create a datasource. 
    - Type: `InfluxDB`
    - Name: `speedtests`
    - HTTP - URL: `http://influxdb:8086`
    - InfluxDB Details - Database: `speedtest_db`
    - InfluxDB Details - User: `db_username`
    - InfluxDB Details - Password: `db_password`

    Import the `grafana_dashboard_template.json` template as a new dashboard.

## Environment Variables

Use OS or Docker environmet variables to configure the program run.

Example: `docker run -d --env DB_ADDRESS= influx_db --env TEST_INTERVAL=120 --name speedtest-influx aidengilmartin/speedtest-influx`
### InfluxDB Settings

| Variable          | Default Value        | Informations                                                 |
|:------------------|:---------------------|:-------------------------------------------------------------|
| DB_ADDRESS        | db_hostname.network  | FQDN of InfluxDB Server                                      |
| DB_PORT           | 8086                 | Port Number of InfluxDB Server                               |
| DB_USER           | db_username          | InfluxDB user name                                           |
| DB_PASSWORD       | db_password          | InfluxDB password                                            |
| DB_DATABASE       | speedtest_db         | InfluxDB database name                                       |
| DB_RETRY_INVERVAL | 60                   | Time before retrying a failed data upload.                   |


### Speedtest Settings

| Variable           | Default Value          | Informations                                               |
|:-------------------|:-----------------------|:-----------------------------------------------------------|
| TEST_INTERVAL      | 1800                   | Time between tests (in seconds).                           |
| TEST_FAIL_INTERVAL | 60                     | Time before retrying a failed Speedtest (in seconds).      |

### Loglevel Settings

| Variable         | Default Value          | Informations                                                                                  |
|:-----------------|:-----------------------|:----------------------------------------------------------------------------------------------|
| PRINT_DATA       | False                  | Print Test Data in Log (True or False)                                                        | 


This repo uses code from both the main fork and the following fork and accounts for the changes made since its creation.
https://github.com/breadlysm/speedtest-to-influxdb
