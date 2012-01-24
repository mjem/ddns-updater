ddns-updater
============

.. contents::
..
    1  Introduction
    2  Configuration
      2.1  Fetch configuration
      2.2  Push configuration
    3  Compatibility

Introduction
------------

Do use namecheap.com for domain registrations? Do you use their dynamic dns service? Do you have a Sitecom N300 router? Would you like a tool which checks for changes to the IP address assigned by your ISP and updates your DNS records automatically? If you answered Yes to all the above, this project could be for you.

This tool may work with other routers and dynamic DNS providers. It requests the external IP address from the router rather than a service such as whatismyip.com to avoid adding a dependancy on a remote service.

Configuration
-------------

Configuration options are supplied wither through a configuration file or command line parameters.

There are 2 parts to `ddns-updater` configuration: configuring how the external IP address is read, and configuring how it is updated.

Fetch configuration
~~~~~~~~~~~~~~~~~~~

The following options are required:

- url
- user
- pass
- search
- skip
- match

* Why use `search`, `skip`, and `match` instead of a simple regular expression? On the Sitecom router the line containing the IP address is simply "<td>1.2.3.4</td>" which is a bit ambigous. But the previous line is "<td>IP Address</td>" which can be searched for.

Push configuration
~~~~~~~~~~~~~~~~~~

Only one configuration option:

- url

i.e.:

    https://dynamicdns.park-your-domain.com/update?
    host=www&'
    domain=example.com&
    password=12345&
    ip={ip}

Replace example.com with your actual domain. Replace www with something else if you use a different subdomain.
DDNS providers other than namecheap.com could use a completely different scheme. This tool only works if your
DDNS provider allows records to be updated with a simple URL ping.

Usage
-----

Run:

    ddns-updated <options>

In the `debian` top level directory is a Debian rc.init style file to run on startup. Copy it to '/etc/init.d'
then use rc-conf or similar to insert it to the system startup programs.

Compatibility
-------------

Python 2.7 is required. This program has been tested on Linux only.
