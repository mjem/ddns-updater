#!/usr/bin/env python2.7

import os
import re
import sys
import time
import urllib2
import logging
import argparse
import functools
import ConfigParser
import xml.etree.ElementTree

from ddnsupdater.log import init_log
from ddnsupdater import __version__


def get_ip(user, password, url, search, skip, match):
	"""Find our the current external IP assigned by the ISP to our router.
	We do this by retrieving a page from the router control site containing the IP.
	Most routers require authentication before giving out this info.

	user
	    HTTP username for Basic authentication

	password
	    HTTP password for Basic authentication

	url
	    URL for page containing external IP

	search
	    String to look for to identify the line containing the IP address

	skip
	    After `search` has been found in a line, skip forwards `skip` lines
		to find the line which actually contains the IP address.

	match
	    Regular expression containing a group which will pick out the IP address
		from the line identified by `search` and `skip`

	>>> get_ip('my-user',
			   'my-password',
			   'http://192.168.0.1/internet-status',
			   '<td>IP Address:'
			   0,
			   '<td>IP Address:([0-9.])')

	"""

	# import requests
	# using Requests module ... doesn't work on my router as it only sends auth credentials
	# on initial retrieve
	# s = requests.session()
	# s.config['keep_alive'] = False  # failed attempt to fix auth problem
	# r = s.get(url, auth=(user, password), config={'verbose':sys.stdout})
	# for line in r.content.split('\n'):

	try:
		response = urllib2.urlopen(url)
	except urllib2.HTTPError as e:
		if e.code != 401:
			raise

		# if we got a 401 code (unauthorised) configure urllib2 for basic authentication
		# and try again.
		# Once configured globally, the module will pass the credentials on subsequent calls
		realm_obj = re.match(r'Basic realm="(.*)"',
							 e.headers.getheader('WWW-Authenticate'))
		if realm_obj is None:
			raise ValueError('Could not find realm in {h}'.format(h=e.headers))

		realm = realm_obj.groups(0)[0]
		auth_handler = urllib2.HTTPBasicAuthHandler()
		auth_handler.add_password(realm=realm,
								  uri=url,
								  user=user,
								  passwd=password)
		opener = urllib2.build_opener(auth_handler)
		urllib2.install_opener(opener)

		response = urllib2.urlopen(url)

	trigger = None
	for line in response.read().split('\n'):
		# logging.debug('LINE: ' + line)
		if trigger is not None:
			trigger -= 1
			if trigger == 0:
				# print 'SKIP ', line
				# print 'matcher ', match
				match_obj = re.match(match, line)
				if match_obj is None:
					raise ValueError('No match found {skip} lines after finding string {search}'.format(
							skip=skip,
							search=search))

				# print ip_match
				match_group = match_obj.groups(1)
				if len(match_group) == 0:
					raise ValueError('No groups in regular expression {match}'.format(match=match))

				# logging.debug('get_ip returning ' + str(match_group[0]))
				return match_group[0]

		## print 'LINE: ', line
		if search in line:
			# print 'MATCH ', line
			trigger = skip

	logging.debug('No IP address found')
	raise ValueError('Cannot find IP address')


def update_ddns(url):
	"""Ping the supplied URL to update the DDNS entry.
	Try and parse the result, assuming the remote service is namecheap.com.
	"""

	response_obj = urllib2.urlopen(url)
	response = response_obj.read()

	try:
		root_elem = xml.etree.ElementTree.fromstring(response)
	# except lxml.etree.XMLSyntaxError:
	except xml.etree.ElementTree.ParseError:
		logging.error('Could not decode server response ({code}): {body}'.format(
				code=response_obj.code,
				body=response))
		return

	err_count_elem = root_elem.find('ErrCount')
	if err_count_elem is not None:
		err_count = err_count_elem.text.strip()
	else:
		err_count = 'Could not decode error count'

	done_elem = root_elem.find('Done')
	if done_elem is not None:
		done = done_elem.text.strip()
	else:
		done = 'Could not decode done value'

	logging.info('Server response ({code}): errors {err} done {done}'.format(
			code=response_obj.code,
			err=err_count,
			done=done))

	# Sample response:

	# <?xml version="1.0"?>
	# <interface-response>
	# <Command>SETDNSHOST</Command>
	# <Language>eng</Language>
	# <IP>87.186.224.7</IP>
	# <ErrCount>0</ErrCount>
	# <ResponseCount>0</ResponseCount>
	# <Done>true</Done>
	# <debug><![CDATA[]]></debug>
	# </interface-response>


def poll(input_function, period, output_url, statefile):
	"""Keep calling `input_function` to retrieve the current IP address,
	and ping `output_url` to update it if a change is seen.
	`output_url` should be a string containing `{ip}` which will be expanded to the current
	address.

	>>> poll(my_func, 600, 'https://dynamicdns.park-your-domain.com/update?'
								 'host=www&'
								 'domain=example.com&'
								 'password=12345&
								 'ip={ip}')

	"""

	last_ip = None
	if statefile is not None:
		if not os.path.exists(statefile):
			logging.info('Statefile ' + statefile + ' not found, will be created')
		else:
			logging.info('Reading statefile ' + statefile)
			with open(statefile, 'r') as h:
				last_ip = h.read().strip()

			logging.info('Read external address of {ip}'.format(ip=last_ip))

	while True:
		# logging.debug('calling ' + str(input_function))
		ip = input_function()
		# reload(requests)  # failed attempt to get Requests module to work
		# with repeat calls
		logging.info('Current external address is ' + ip)
		if ip != last_ip:
			url = output_url.format(ip=ip)
			# don't log IP as it will probably contain a password
			logging.info('External IP changed, updating DDNS server')
			update_ddns(url)
			logging.info('Updating statefile ' + statefile)
			with open(statefile, 'w') as h:
				h.write(ip)

		last_ip = ip
		logging.debug('Sleeping for {period} seconds'.format(period=period))
		time.sleep(period)

def configure_defaults_from_file(config_file, defaults):
	"""Read a set of values from `config_file` and assign them to the `defaults`
	dictionary.
	"""

	config = ConfigParser.ConfigParser()

	if not os.path.exists(config_file):
		raise IOError('Configuration file {name} cannot be read'.format(
				name=config_file))

	config.read(config_file)

	if config.has_option('ddnsupdater', 'sleep'):
		defaults['sleep'] = config.getint('ddnsupdater', 'sleep')

	if config.has_option('ddnsupdater', 'logging'):
		# set log config file name relative to config file name
		defaults['logging'] = os.path.join(
			os.path.dirname(os.path.abspath(config_file)),
							 config.get('ddnsupdater', 'logging'))

	if config.has_option('ddnsupdater', 'statefile'):
		defaults['statefile'] = config.get('ddnsupdater', 'statefile')

	if config.has_option('fetch', 'url'):
		defaults['fetch_url'] = config.get('fetch', 'url')

	if config.has_option('fetch', 'user'):
		defaults['fetch_user'] = config.get('fetch', 'user')

	if config.has_option('fetch', 'password'):
		defaults['fetch_password'] = config.get('fetch', 'password')

	if config.has_option('fetch', 'search'):
		defaults['fetch_search'] = config.get('fetch', 'search')

	if config.has_option('fetch', 'skip'):
		defaults['fetch_skip'] = config.getint('fetch', 'skip')

	if config.has_option('fetch', 'match'):
		defaults['fetch_match'] = config.get('fetch', 'match')

	if config.has_option('push', 'url'):
		defaults['push_url'] = config.get('push', 'url')


def main():
	# parser = argparse.ArgumentParser()
	parser = argparse.ArgumentParser(
		prog='ddns-updater',
		version=__version__,
		description=('Continually update a Dynamic DNS server to the current external IP address '
					 'read from a router.'),
		add_help=False)
	parser.add_argument('--config', '--conf', '-c',
						metavar='FILE',
						help='Read configuration from FILE')
	args, remaining_argv = parser.parse_known_args()
	defaults = {
		'sleep': 3600,
		'fetch_user': 'admin',
		'fetch_search': 'IP Address',
		'fetch_skip': 0,
		'fetch_match': r'.*<td>([0-9.]+)',
		'push_url': ('https://dynamicdns.park-your-domain.com/update?'
					 'host=www&'
					 'domain=example.com&'
					 'password=12345&'
					 'ip={ip}'),
		}

	if args.config is not None:
		# If the user supplied a --config file, parse it and add the contents to our
		# defaults dictionary.
		# Settings can then be overridden with command line flags.
		configure_defaults_from_file(args.config, defaults)

	parser.set_defaults(**defaults)
	parser.add_argument('--help', '-h',
						action='store_true',
						help='show this help message and exit')
	parser.add_argument('--logging',
						metavar='FILE',
						help='Configure logging using FILE')
	parser.add_argument('--statefile',
						help=('Optional statefile used to record external IP between invocations '
							  'to avoid reconfiguring the dynamic DNS server on every startup'))
	parser.add_argument('--sleep',
						type=int,
						help='Time between external IP address polls in seconds')
	parser.add_argument('--fetch-user',
						help='HTTP username to use for request')
	parser.add_argument('--fetch-password',
						help='HTTP password to use for request')
	parser.add_argument('--fetch-url',
						help='Router URL containing external IP address')
	parser.add_argument('--fetch-search',
						metavar='SEARCH',
						help=('Search string to look for to identify line containing '
							  'external IP address'))
	parser.add_argument('--fetch-skip',
						metavar='COUNT',
						help='Skip forwards COUNT lines from line containing MATCH')
	parser.add_argument('--fetch-match',
						help='Regular expression including one group to pick out IP address')
	parser.add_argument('--one-shot',
						action='store_true',
						help='Test configuration by just retrieving IP address')
	parser.add_argument('--push-url',
						help=('Target IP address to ping to update IP address. '
							  'Use {ip} as placeholder for actual address'))

	args = parser.parse_args()

	if args.help:
		parser.print_help()
		parser.exit()

	init_log(args.logging)

	if args.fetch_url is None:
		parser.error('No URL configured to fetch external IP address. Use --fetch-url or '
					 'the config file setting to specify a URL')

	# Create a curried version of `get_ip()` with all parameters fixed
	fetch_function = functools.partial(get_ip,
									   user=args.fetch_user,
									   password=args.fetch_password,
									   url=args.fetch_url,
									   search=args.fetch_search,
									   skip=args.fetch_skip,
									   match=args.fetch_match)

	if args.one_shot:
		print fetch_function()

	poll(input_function=fetch_function,
		 period=args.sleep,
		 output_url=args.push_url,
		 statefile=args.statefile)

if __name__ == '__main__':
	main()
