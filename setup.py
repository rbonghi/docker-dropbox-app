# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/docker-dropbox-app or http://rnext.it).
# Copyright (c) 2020 Raffaello Bonghi.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# io.open is needed for projects that support Python 2.7
# It ensures open() defaults to text mode with universal newlines,
# and accepts an argument to specify the text encoding
# Python 3 only projects can skip this import
from io import open
# Launch command
import os
import re


here = os.path.abspath(os.path.dirname(__file__))
project_homepage = "https://github.com/rbonghi/docker-dropbox-app"
documentation_homepage = "https://rbonghi.github.io/docker-dropbox-app"


with open(os.path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    requirements = f.read().splitlines()


# Get the long description from the README file
with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Load version package
with open(os.path.join(here, "dbsync", "__init__.py")) as fp:
    VERSION = (
        re.compile(r""".*__version__ = ["'](.*?)['"]""", re.S).match(fp.read()).group(1)
    )
# Store version package
version = VERSION


# Configuration setup module
setup(
    name="dbsync",
    version=version,
    author="Raffaello Bonghi",
    author_email="raffaello@rnext.it",
    description="Automatic sync folder by a dropbox app",
    license='MIT',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url=project_homepage,
    download_url=(project_homepage + "/archive/master.zip"),
    project_urls={
        "How To": documentation_homepage,
        "Examples": (project_homepage + "/tree/master/examples"),
        "Bug Reports": (project_homepage + "/issues"),
        "Source": (project_homepage + "/tree/master")
    },
    packages=find_packages(exclude=['examples', 'scripts', 'tests']),  # Required
    # Define research keywords
    keywords=("dropbox syncronization docker"),
    classifiers=["Development Status :: 5 - Production/Stable",
                 # Audiencence and topics
                 "Intended Audience :: Developers",
                 # License
                 "License :: OSI Approved :: MIT",
                 # Programming and Operative system
                 "Programming Language :: Unix Shell",
                 "Programming Language :: Python :: 3",
                 "Programming Language :: Python :: 3.4",
                 "Programming Language :: Python :: 3.5",
                 "Programming Language :: Python :: 3.6",
                 "Programming Language :: Python :: 3.7",
                 "Programming Language :: Python :: 3.8",
                 "Operating System :: POSIX :: Linux",
                 ],
    # Install requirements
    install_requires=requirements,
    # Requisites
    # https://packaging.python.org/guides/distributing-packages-using-setuptools/#python-requires
    python_requires='>=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, <4',
    platforms=["linux", "linux2", "darwin"],
    # Zip safe configuration
    # https://setuptools.readthedocs.io/en/latest/setuptools.html#setting-the-zip-safe-flag
    zip_safe=False,
    # The following provide a command called `dbsync`
    entry_points={'console_scripts': ['dbsync=dbsync.__main__:main']},
)
# EOF
