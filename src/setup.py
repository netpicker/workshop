from setuptools import find_packages, setup

setup(
    name='slurpit_netbox',
    version='0.1.66',
    description="Sync Slurp'IT into NetBox",
    install_requires=[
        'requests', 'httpx'
    ],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)