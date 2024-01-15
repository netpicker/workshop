FROM netboxcommunity/netbox:latest

RUN pip install --upgrade pip && pip install poetry

COPY /docker/configuration/configuration.py /etc/netbox/config/configuration.py
COPY /docker/configuration/plugins.py /etc/netbox/config/plugins.py

COPY src/ /sluprit_netbox/src/
COPY pyproject.toml /sluprit_netbox/pyproject.toml

WORKDIR /sluprit_netbox
RUN poetry install
WORKDIR /

