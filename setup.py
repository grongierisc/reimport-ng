from setuptools import setup, find_packages
import sys, os

version = '1.2'

setup(name='reimport',
    version=version,
    description="deep reload for python modules",
    long_description="""\
This module intends to be a full featured replacement for Python's
reload function. It is targeted towards making a reload that works
for Python plugins and extensions used by longer running applications.""",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Libraries :: Python Modules"
        "Programming Language :: Python",
        ],
    keywords='reload reimport',
    author='Peter Shinners',
    author_email='pete@shinners.org',
    url='http://code.google.com/p/reimport/',
    license='MIT',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=False,
    zip_safe=True,
    )

