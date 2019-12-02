#!/usr/bin/env python3

from datetime import datetime
import io
import os
import pytz

import atoma
from minio import Minio
import requests


MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY')
MINIO_SERVER = os.getenv('MINIO_SERVER')
TRAVIS_ACCESS_TOKEN = os.getenv('TRAVIS_ACCESS_TOKEN')


# FIXME(berendt): move to YAML file
REPOSITORIES = {
    'ceph-luminous': {
        'repository': 'ceph/ceph-ansible',
        'branch': 'stable-3.2',
        'target': {
            'repository': 'docker-ceph-ansible',
            'version': 'luminous',
            'parameter': 'CEPH_VERSION'
        }
    },
    'ceph-nautilus': {
        'repository': 'ceph/ceph-ansible',
        'branch': 'stable-4.0',
        'target': {
            'repository': 'docker-ceph-ansible',
            'version': 'nautilus',
            'parameter': 'CEPH_VERSION'
        }
    },
    'ceph-master': {
        'repository': 'ceph/ceph-ansible',
        'branch': 'master',
        'target': {
            'repository': 'docker-ceph-ansible',
            'version': 'master',
            'parameter': 'CEPH_VERSION'
        }
    },
    'openstack-queens': {
        'repository': 'openstack/kolla-ansible',
        'branch': 'stable/queens',
        'target': {
            'repository': 'docker-kolla-ansible',
            'version': 'queens',
            'parameter': 'OPENSTACK_VERSION'
        }
    },
    'openstack-rocky': {
        'repository': 'openstack/kolla-ansible',
        'branch': 'stable/rocky',
        'target': {
            'repository': 'docker-kolla-ansible',
            'version': 'rocky',
            'parameter': 'OPENSTACK_VERSION'
        }
    },
    'openstack-stein': {
        'repository': 'openstack/kolla-ansible',
        'branch': 'stable/stein',
        'target': {
            'repository': 'docker-kolla-ansible',
            'version': 'stein',
            'parameter': 'OPENSTACK_VERSION'
        }
    },
    'openstack-master': {
        'repository': 'openstack/kolla-ansible',
        'branch': 'master',
        'target': {
            'repository': 'docker-kolla-ansible',
            'version': 'master',
            'parameter': 'OPENSTACK_VERSION'
        }
    }
}


def trigger_build(repository, branch, message):

    print("Triggering %s @ %s" % (REPOSITORIES[repository]['target']['version'], REPOSITORIES[repository]['target']['repository']))

    url = "https://api.travis-ci.org/repo/osism%%2F%s/requests" % REPOSITORIES[repository]['target']['repository']
    headers = {
        'Travis-API-Version': '3',
        'Authorization': "token %s" % TRAVIS_ACCESS_TOKEN
    }
    target_parameter = REPOSITORIES[repository]['target']['parameter']
    target_version = REPOSITORIES[repository]['target']['version']
    json = {
        'request': {
            'branch': 'master',
            'message': message,
            "config": {
                "env": {
                    "global": ["%s=%s" % (target_parameter, target_version)]
                }
            }
        }
    }

    response = requests.post(url, headers=headers, json=json)


def check_repository(repository, branch):
    mc = Minio(MINIO_SERVER, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=True)

    try:
        mc.make_bucket("trigger")
    except:
        pass

    try:
        last_updated = mc.get_object('trigger', "%s/updated" % repository)
        last_updated = datetime.strptime(last_updated.data.decode('ascii'), '%Y-%m-%dT%H:%M:%SZ')
        last_updated = pytz.utc.localize(last_updated)
    except:
        last_updated = datetime(1970, 1, 1, tzinfo=pytz.UTC)

    url = "https://github.com/%s/commits/%s.atom" % (REPOSITORIES[repository]['repository'], branch)
    response = requests.get(url)
    feed = atoma.parse_atom_bytes(response.content)
    updated = feed.updated

    if updated > last_updated:
        last_entry = feed.entries[0]
        commit = last_entry.links[0].href.split('/')[-1]
        message = "%s (%s, %s)" % (REPOSITORIES[repository]['repository'], branch, commit)
        trigger_build(repository, branch, message)

    store = updated.strftime('%Y-%m-%dT%H:%M:%SZ').encode('utf-8')

    try:
        mc.put_object('trigger', "%s/updated" % repository, io.BytesIO(store), len(store))
    except:
        pass


def main():
    for repository in REPOSITORIES:
        print("Checking %s @ %s" % (REPOSITORIES[repository]['branch'], REPOSITORIES[repository]['repository']))
        check_repository(repository, REPOSITORIES[repository]['branch'])


if __name__ == '__main__':
    main()
