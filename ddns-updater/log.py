#!/usr/bin/env python2.7

"""Initialise Python standard library logging module"""

import logging
import logging.config

LOGGING = {
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


def init_log(filename=None):
	"""Initialise log file"""
	if filename is not None:
		LOGGING['handlers']['file'] = {'class': 'logging.FileHandler',
									   'filename': filename,
									   'formatter': 'normal'}
		LOGGING['root']['handlers'] = ['file']

	logging.config.dictConfig(LOGGING)
