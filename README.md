# NetBox Discovery Plugin
[Netbox](https://github.com/netbox-community/netbox) plugin to automatically discover your network with [Slurp'it](https://slurpit.io).

## Compatibility

| NetBox Version | Plugin Version |
|----------------|----------------|
|   NetBox 3.7   |    >= 0.8.0    |

## Installation

The plugin is available as a Python package in [pypi](https://pypi.org/project/slurpit-netbox/) and can be installed with pip  

```
pip install slurpit-netbox
```
Enable the plugin in /opt/netbox/netbox/netbox/configuration.py:
```
PLUGINS = ['slurpit_netbox']
```
Restart NetBox and add `slurpit-netbox` to your requirements.txt

See [NetBox Documentation](https://docs.netbox.dev/en/stable/plugins/#installing-plugins) for details

## Getting started
On our [getting started page](https://slurpit.io/getting-started/) you can take an Online Course to understand how the plugin works, or play with the plugin in a simulated network in our Sandbox.