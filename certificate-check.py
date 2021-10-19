#!/usr/bin/python3

import os, re, sys, subprocess, yaml
from datetime import datetime

# This script should be run as a cron job to check the cert and then trigger the ansible playbook to 
# update cert if required
# Add the site check to the data variable

config = """
minimum_remaining_days: 14
"""

data = yaml.load(open("vars.yaml", "r"), Loader=yaml.FullLoader)
SITES = data["cert_domains"]
print(SITES)
CONFIG = yaml.load(config, Loader=yaml.FullLoader)

output = []

datenow = datetime.now()

for site in SITES:
    print("Processing %s" % site['name'])

    url = site['test_url'] if 'test_url' in site else '%s:443' % site['name']

    command = '''echo | openssl s_client -servername {servername} -connect {url} 2>/dev/null \
        | openssl x509 -noout -dates | grep 'notAfter=' | cut -f 2 -d='''.format(
            servername=site['name'],
            url=url
        )

    p = subprocess.Popen(
        command,
        shell=True, stdout=subprocess.PIPE)
    expiry_date_str, _ = p.communicate()
    print("expiry_date_str: %s" % expiry_date_str)
    expiry_date = datetime.strptime(expiry_date_str[0:-1].decode('utf-8'), r'%b %d %H:%M:%S %Y %Z')
    remaining_days = (expiry_date - datenow).days
    print("remaining days: %s" % remaining_days)
    try:
      minimum_remaining_days = site['minimum_remaining_days']
    except:
      minimum_remaining_days = CONFIG['minimum_remaining_days']
    if remaining_days <= minimum_remaining_days:
        output.append({'name': site['name'], 'remaining_days': remaining_days, 'minimum_remaining_days': minimum_remaining_days})

if os.path.exists('output.txt'):
    os.remove('output.txt')

if len(output) > 0:
    print("CRITICAL. Some sites certificate will expire very soon. See below.")
    print(output)
    import json
    open('output.txt','w').write(json.dumps(output, indent=4))
    current_dir = os.path.dirname(os.path.realpath(__file__))
    cmd = f"cd {current_dir} && ansible-playbook play.yaml"
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    p.communicate()
else:
    print("All good. All remaining_days are greater than %s" % CONFIG['minimum_remaining_days'])
