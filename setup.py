from codecs import open
import re
from setuptools import setup, find_packages

setup(
    name='kleroteria',
    # this version doesn't really mean anything since this ships as an app.
    # it's also hardcoded in the requirements files.
    version='0.0.1',
    description='An email lottery and spiritual successor to The Listserve.',

    author='Simon Weber',
    author_email='simon@simonmweber.com',

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python :: 3.8',
    ],

    packages=find_packages(exclude=['tests']),

    install_requires=[
        'boto3>1.27',
        'raven',
    ],

    include_package_data=True,
)
