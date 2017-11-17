import argparse
import time

import wget
from boto.ec2 import connect_to_region

from boto.manage.cmdshell import sshclient_from_instance


def read_config(config_file='.config'):
    cfg = dict()
    with open(config_file, 'r') as f:
        for line in f:
            key, value = line.strip().split('=')
            cfg[key] = value
    return cfg


def connect_and_download(config_file):
    cfg = read_config(config_file)
    region = cfg['region']
    aws_access_key_id = cfg['aws_access_key_id']
    aws_secret_access_key = cfg['aws_secret_access_key']
    instance_ami = cfg['instance_ami']
    ssh_key = cfg['ssh_key']
    key_name = cfg['key_name']

    print "Connecting to region"
    conn = connect_to_region(region,
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key)

    print "Starting instance from image {}".format(instance_ami)
    start_time = time.time()
    reservation = conn.run_instances(instance_ami,
                                     instance_type='t2.micro',
                                     key_name=key_name,
                                     security_groups=['launch-wizard-2'])

    instance = reservation.instances[0]
    print "Spawned instance: {}".format(instance)

    print "Waiting for the instance to be ready..."
    while instance.state != 'running':
        time.sleep(0.1)
        instance.update()
    startup_time = time.time() - start_time
    print "Startup time: {}".format(startup_time)
    print "Waiting 30 seconds to be able to set an ssh client up..."
    time.sleep(30)

    ssh_client = sshclient_from_instance(instance, ssh_key, user_name='ubuntu')

    print "Starting apache2 daemon"
    status, stdout, _ = ssh_client.run('sudo service apache2 start')

    print "Waiting for the daemon to be started..."
    while True:
        status, stdout, _ = ssh_client.run('sudo service apache2 status')
        if "active (running)" in stdout:
            "WWW server is ready"
            break
        time.sleep(0.5)

    url = "http://{}/index.html".format(instance.public_dns_name)
    print "Downloading {}".format(url)

    wget.download(url)

    print "Shutting the instance down"
    conn.terminate_instances(instance_ids=[instance.id])

    print "Finished"


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sample AWS Python client')
    parser.add_argument('--config', default='.config')

    args = parser.parse_args()

    connect_and_download(args.config)
