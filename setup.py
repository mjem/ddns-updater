#!/usr/bin/env python

import os

if 'PYTHONDONTWRITEBYTECODE' in os.environ:
	del os.environ['PYTHONDONTWRITEBYTECODE']

import distribute_setup
distribute_setup.use_setuptools()

from setuptools import setup, find_packages

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

execfile('ddnsupdater/__init__.py')

setup(
    name='ddns-updater',
    version=__version__,
    author='Mike Elson',
    author_email='mike.elson@gmail.com',
    url='http://github.com/mjem/ddns-updater',
    description='Daemon to read external IP from a router and update a namecheap.com DDNS record',
	license='GPL',
	keywords="namecheap namecheap.com ddns",
	packages=['ddnsupdater'],
	#scripts=['bin/carrie'],
	entry_points={
		'console_scripts': [
			'ddns-updater=ddnsupdater.main:main',
			]},
	package_dir={'ddnsupdater': 'ddnsupdater'},
	# Files go into MANIFEST.in to get them in the distribution archives,
	# package_data to get them installed
	# package_data={'carrie': ['static/*.js',
							 # 'static/*.css',
							 # 'templates/*.html',
							 # 'static/jquery-ui/js/*.js',
							 # 'static/jquery-ui/css/smoothness/*.css',
							 # 'static/jquery-ui/css/smoothness/images/*.png']},
	long_description=read('README.md'),
    classifiers=[
		'Topic :: Internet :: Name Service (DNS)',
		'License :: OSI Approved :: GNU General Public License (GPL)',
		'Operating System :: POSIX :: Linux',
		'Programming Language :: Python :: 2.7',
		'Topic :: Internet'
    ],
)
