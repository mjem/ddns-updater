#!/usr/bin/env python2.7

import os
import re
import sys
import time
import urllib2
import logging
import argparse
import functools

from lxml import etree

from ddns.log import init_log


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
	response_obj = urllib2.urlopen(url)
	response = response_obj.read()

	try:
		root_elem = etree.fromstring(response)
	except lxml.etree.XMLSyntaxError:
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
		done = 'Count not decode done value'

	logging.info('Server response ({code}): errors {err} done {done}'.format(
			code=response_obj.code,
			err=err_count,
			done=done))

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
			with open(statefile, 'r') as h:
				last_ip = h.read().strip()

			logging.info('Read external address of {ip} from {statefile}'.format(
					ip=last_ip,
					statefile=statefile))

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

def main():
	init_log()
	parser = argparse.ArgumentParser()
	parser.add_argument('-v')
	parser.add_argument('--config',
						metavar='FILE',
						help='Read default values from FILE')
	parser.add_argument('--statefile',
						help=('Optional statefile used to record external IP between invocations '
							  'to reconfiguring the dynamic DNS server on every startup'))
	parser.add_argument('--fetch-user',
						default='admin',
						help='HTTP username to use for request')
	parser.add_argument('--fetch-password',
						default='extropia',
						help='HTTP password to use for request')
	parser.add_argument('--fetch-url',
						default='http://192.168.0.1/s_internet.htm')
	parser.add_argument('--fetch-search',
						default='IP Address')
	parser.add_argument('--fetch-skip',
						default=1)
	parser.add_argument('--fetch-match',
						default=r'.*<td>([0-9.]+)')
	parser.add_argument('--sleep',
						type=int,
						default=3600,
						help='Time between external IP address polls in seconds')
	parser.add_argument('--one-shot',
						action='store_true',
						help='Test configuration by just retrieving IP address')
	parser.add_argument('--push-url',
						default=('https://dynamicdns.park-your-domain.com/update?'
								 'host=www&'
								 'domain=diepunyhumans.org&'
								 'password=f128a6434f224d7bab3b71995228bbd3&'
								 'ip={ip}'),
						help=('Target IP address to ping to update IP address. '
							  'Use {ip} as placeholder for actual address'))

	args = parser.parse_args()

	fetch_function = functools.partial(get_ip,
									   user=args.fetch_user,
									   password=args.fetch_password,
									   url=args.fetch_url,
									   search=args.fetch_search,
									   skip=args.fetch_skip,
									   match=args.fetch_match)

	if args.sleep is not None:
		poll(input_function=fetch_function,
			 period=args.sleep,
			 output_url=args.push_url,
			 statefile=args.statefile)

	print fetch_function()

if __name__ == '__main__':
	main()
