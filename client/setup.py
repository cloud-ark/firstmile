#!/usr/bin/env python

PROJECT = 'cld'

# Change docs/sphinx/conf.py too!
VERSION = '0.1'

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
    author_email='kulkarni.devdatta@gmail.com',

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
            'service provision = cldcmds.service:ServiceDeploy',
            'service show = cldcmds.service:ServiceShow',
        ],
    },

    zip_safe=False,
)
