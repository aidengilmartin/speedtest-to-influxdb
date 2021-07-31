FROM python:3.8-slim-buster

LABEL maintainer="Aiden Gilmartin" \
    description="Speedtest to InfluxDB data bridge"

# Install dependencies
ENV DEBIAN_FRONTEND=noninteractive

COPY requirements.txt /

RUN apt-get update && \
    apt-get dist-upgrade -y && \
    apt-get -q -y install --no-install-recommends curl apt-utils gnupg1 apt-transport-https dirmngr && \
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 379CE192D401AB61

# get speedtest repo from ookla
RUN curl -s https://install.speedtest.net/app/cli/install.deb.sh | bash

RUN apt-get update && apt-get -q -y install speedtest && \
    apt-get -q -y autoremove && \
    apt-get -q -y clean && \
    rm -rf /var/lib/apt/lists/* && \
    pip3 install -r /requirements.txt

# Final setup & execution
COPY speedtest2influx.py /app/speedtest2influx.py
WORKDIR /app
CMD ["python3", "-u", "speedtest2influx.py"]
