#!/usr/bin/env python

PROJECT = 'cld'

# Change docs/sphinx/conf.py too!
VERSION = '1.0.0.rc2'

from setuptools import setup, find_packages

try:
    long_description = open('README.rst', 'rt').read()
except IOError:
    long_description = ''

setup(
    name=PROJECT,
    version=VERSION,

    description='CLD CLI',
    long_description=long_description,

    author='Devdatta Kulkarni',
    author_email='devdattakulkarni@gmail.com',

    url='',
    download_url='',

    classifiers=['Development Status :: 3 - Alpha',
                 'License :: OSI Approved :: Apache Software License',
                 'Programming Language :: Python',
                 'Programming Language :: Python :: 2',
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3',
                 'Programming Language :: Python :: 3.2',
                 'Intended Audience :: Developers',
                 'Environment :: Console',
                 ],

    platforms=['Any'],

    scripts=[],

    provides=[],
    install_requires=['cliff'],

    namespace_packages=[],
    packages=find_packages(),
    include_package_data=True,

    entry_points={
        'console_scripts': [
            'cld = cldcmds.main:main'
        ],
        'cld.cmds': [
            'app deploy = cldcmds.deploy:Deploy',
            'app show = cldcmds.show:Show',
            'app list = cldcmds.app_list:AppList',
            'app delete = cldcmds.app_delete:AppDelete',
            'app logs = cldcmds.app_logs:AppLogs',
            'service provision = cldcmds.service:ServiceDeploy',
            'service delete = cldcmds.service_delete:ServiceDelete',
            'service restrict-access = cldcmds.service_secure:ServiceSecure',
            'service show = cldcmds.service:ServiceShow',
            'service list = cldcmds.service_list:ServiceList',
            'cloud reset = cldcmds.cloud_reset:CloudReset',
            'cloud setup = cldcmds.cloud_setup:CloudSetup',
            'fm logs = cldcmds.fm_actions:FirstMileLogs',
            'fm restart = cldcmds.fm_actions:FirstMileRestart',
            'fm cleanup = cldcmds.fm_actions:FirstMileCleanup',
        ],
    },

    zip_safe=False,
)
