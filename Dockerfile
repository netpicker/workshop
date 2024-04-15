FROM netboxcommunity/netbox:v3.7

# RUN pip install --upgrade pip && pip install poetry

COPY /docker/configuration/configuration.py /etc/netbox/config/configuration.py
COPY /docker/configuration/plugins.py /etc/netbox/config/plugins.py

RUN pip install djangorestframework-bulk
RUN pip install --no-cache-dir slurpit_netbox

# RUN apt-get update && apt-get install -y git
# RUN git clone https://github.com/netbox-community/devicetype-library.git /tmp/repository \
#     && mkdir -p /devicetype-library \
#     && cp -r /tmp/repository/device-types /devicetype-library/device-types \
#     && cp -r /tmp/repository/module-types /devicetype-library/module-types

# COPY src/ /slurpit_netbox/src/
# COPY pyproject.toml /slurpit_netbox/pyproject.toml
# COPY README.md /slurpit_netbox/README.md

# WORKDIR /slurpit_netbox
# RUN  poetry config virtualenvs.create false \
#     && poetry install --no-dev\
#     && . /opt/netbox/venv/bin/activate

# RUN  poetry build
# WORKDIR /slurpit_netbox/dist
# RUN latest_wheel=$(ls -1t | grep .whl | head -n 1) \
#     && pip install "${latest_wheel}" 
# WORKDIR /opt/netbox/netbox

