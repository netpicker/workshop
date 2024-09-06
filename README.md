# NetBox Discovery Plugin
[Netbox](https://github.com/netbox-community/netbox) plugin to automatically discover your network with [Slurp'it](https://slurpit.io).

## Compatibility

| NetBox Version | Plugin Version |
|----------------|----------------|
|   NetBox 4.1   |    In progress |
|   NetBox 4.0   |    >= 0.9.x    |
|   NetBox 3.7   |    >= 0.8.x    |

## Installation

The plugin is available as a Python package in [pypi](https://pypi.org/project/slurpit_netbox/) and can be installed with pip  

```
pip install --no-cache-dir slurpit_netbox
```
Enable the plugin in /opt/netbox/netbox/netbox/configuration.py:
```
PLUGINS = ['slurpit_netbox']
```
Restart NetBox and add `slurpit_netbox` to your requirements.txt

See [NetBox Documentation](https://docs.netbox.dev/en/stable/plugins/#installing-plugins) for details

## Getting started
On our [getting started page](https://slurpit.io/getting-started/) you can take an Online Course to understand how the plugin works, or play with the plugin in a simulated network in our Sandbox.

## Changelog
Changelog can be found here: https://slurpit.io/knowledge-base/netbox-plugin-changelog

## Training videos
We made a series of videos on how to use Slurp'it and NetBox.
https://slurpit.io/online-courses/

