import json

from setuptools import setup

with open("deployer_deploy/package_info.json", "r") as file:
    info = json.loads(file.read())

setup(
    name='deployer',
    version=info.get("version"),
    py_modules=['deployer_deploy'],
    install_requires=[
        'Click',
    ],
    entry_points='''
        [console_scripts]
        deployer=deployer_deploy.deploy:cli
    ''',
)
