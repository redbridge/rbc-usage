from setuptools import setup, find_packages
from glob import glob

name = 'rbc-usage'

with open('requirements.txt', 'r') as f:
        requires = [x.strip() for x in f if x.strip()]

conf_files = [ ('conf', glob('conf/*.cfg')) ]
dirs = [('log', [])]
data_files =  conf_files + dirs

setup(
    name=name,
    version='0.4',
    author='RedBridge AB',
    data_files = data_files,
    packages=['rbc_usage','rbc_usage.collectors', 'rbc_usage.webapp', 'rbc_usage.common'],
    scripts=glob('bin/*'),
    install_requires=requires,
    entry_points = {
                'console_scripts': [
                        'rbc-import-cloudusage=rbc_usage.collectors.cloudusage:main',
                        'rbc-import-swift=rbc_usage.collectors.swiftusage:main'
                ],
    }
)
