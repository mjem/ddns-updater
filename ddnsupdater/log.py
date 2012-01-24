#!/usr/bin/env python2.7

"""Initialise Python standard library logging module"""

import os
import logging
import logging.config

CONSOLE_LOGGING = {
	'version': 1,
		'disable_existing_loggers': True,
		'formatters': {
			'normal': {
				'format': '%(asctime)s %(levelname)s %(message)s',
				'datefmt': '%Y-%m-%d %H:%M:%S',
				},
			},
		'handlers': {
			'console': {  # 'level': 'DEBUG',
						'class': 'logging.StreamHandler',
						'formatter': 'normal',
						},
			},
		'root': {
				'level': 'DEBUG',
				'handlers': ['console'],
				},
		}


def init_log(config_filename=None):
	"""Initialise log file"""
	if config_filename is None:
		logging.config.dictConfig(CONSOLE_LOGGING)

	else:
		if not os.path.exists(config_filename):
			raise IOError('Log config file {name} cannot be read'.format(
					name=config_filename))

		logging.config.fileConfig(config_filename)

		# LOGGING['handlers']['file'] = {'class': 'logging.FileHandler',
									   # 'filename': filename,
									   # 'formatter': 'normal'}
		# LOGGING['root']['handlers'] = ['file']

