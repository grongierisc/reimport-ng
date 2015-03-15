from setuptools import setup, find_packages

version = '1.4.1'

setup(name='reimport',
    version=version,
    description="deep reload for python modules",
    py_modules=["reimport"],
    long_description="""\
This module intends to be a full featured replacement for Python's
reload function. It is targeted towards making a reload that works
for Python plugins and extensions used by longer running applications.""",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Libraries :: Python Modules",
        'Programming Language :: Python :: 2',
        ],
    keywords='reload reimport',
    author='Peter Shinners',
    author_email='pete@shinners.org',
    url='https://bitbucket.org/petershinners/reimport',
    license='MIT',
    include_package_data=True,
    zip_safe=True,
    )

