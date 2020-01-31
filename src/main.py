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
RESSOURCES = {
    'ceph-daemon': {
        'type': 'docker',
        'image': 'ceph/daemon',
        'tag': 'latest',
        'target': {
            'image': 'osism/ceph-daemon',
            'repository': 'docker-ceph-container',
            'version': 'latest',
            'parameter': 'VERSION'
        }
    },
    'ceph-luminous': {
        'type': 'git',
        'repository': 'ceph/ceph-ansible',
        'branch': 'stable-3.2',
        'target': {
            'repository': 'docker-ceph-ansible',
            'version': 'luminous',
            'parameter': 'CEPH_VERSION'
        }
    },
    'ceph-nautilus': {
        'type': 'git',
        'repository': 'ceph/ceph-ansible',
        'branch': 'stable-4.0',
        'target': {
            'repository': 'docker-ceph-ansible',
            'version': 'nautilus',
            'parameter': 'CEPH_VERSION'
        }
    },
    'ceph-master': {
        'type': 'git',
        'repository': 'ceph/ceph-ansible',
        'branch': 'master',
        'target': {
            'repository': 'docker-ceph-ansible',
            'version': 'master',
            'parameter': 'CEPH_VERSION'
        }
    },
    'openstack-queens': {
        'type': 'git',
        'repository': 'openstack/kolla-ansible',
        'branch': 'stable/queens',
        'target': {
            'repository': 'docker-kolla-ansible',
            'version': 'queens',
            'parameter': 'OPENSTACK_VERSION'
        }
    },
    'openstack-rocky': {
        'type': 'git',
        'repository': 'openstack/kolla-ansible',
        'branch': 'stable/rocky',
        'target': {
            'repository': 'docker-kolla-ansible',
            'version': 'rocky',
            'parameter': 'OPENSTACK_VERSION'
        }
    },
    'openstack-stein': {
        'type': 'git',
        'repository': 'openstack/kolla-ansible',
        'branch': 'stable/stein',
        'target': {
            'repository': 'docker-kolla-ansible',
            'version': 'stein',
            'parameter': 'OPENSTACK_VERSION'
        }
    },
    'openstack-master': {
        'type': 'git',
        'repository': 'openstack/kolla-ansible',
        'branch': 'master',
        'target': {
            'repository': 'docker-kolla-ansible',
            'version': 'master',
            'parameter': 'OPENSTACK_VERSION'
        }
    },
    'docker-openstack-master': {
        'type': 'git',
        'repository': 'openstack/kolla',
        'branch': 'master',
        'target': {
            'repository': 'docker-kolla-docker',
            'version': 'master',
            'parameter': 'TRAVIS_OPENSTACK_VERSION'
        }
    }
}


def trigger_build(repository, branch, message):

    print("Triggering %s @ %s" % (RESSOURCES[repository]['target']['version'], RESSOURCES[repository]['target']['repository']))

    url = "https://api.travis-ci.org/repo/osism%%2F%s/requests" % RESSOURCES[repository]['target']['repository']
    headers = {
        'Travis-API-Version': '3',
        'Authorization': "token %s" % TRAVIS_ACCESS_TOKEN
    }
    target_parameter = RESSOURCES[repository]['target']['parameter']
    target_version = RESSOURCES[repository]['target']['version']

    if RESSOURCES[repository]['type'] == 'git':
        env = {
            'global': [
                "%s=%s" % (target_parameter, target_version)
            ]
        }
    elif RESSOURCES[repository]['type'] == 'docker':
        env = {
            'global': [
                "%s=%s" % (target_parameter, target_version),
                "REPOSITORY=%s" % RESSOURCES[repository]['target']['image']
            ]
        }

    json = {
        'request': {
            'branch': 'master',
            'message': message,
            'config': {
                'env': env
            }
        }
    }

    response = requests.post(url, headers=headers, json=json)


def check_image(image, tag):
    mc = Minio(MINIO_SERVER, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=True)

    try:
        mc.make_bucket("trigger")
    except:
        pass

    try:
        last_updated = mc.get_object('trigger', "%s/updated" % image)
        last_updated = datetime.strptime(last_updated.data.decode('ascii'), '%Y-%m-%dT%H:%M:%S.%fZ')
        last_updated = pytz.utc.localize(last_updated)
    except:
        last_updated = datetime(1970, 1, 1, tzinfo=pytz.UTC)

    url = "https://hub.docker.com/v2/repositories/%s/tags/%s" % (RESSOURCES[image]['image'], tag)
    response = requests.get(url)
    updated_str = response.json()['last_updated']
    updated = datetime.strptime(updated_str, '%Y-%m-%dT%H:%M:%S.%fZ')
    updated = pytz.utc.localize(updated)

    if updated > last_updated:
        message = "%s (%s)" % (RESSOURCES[image]['image'], tag)
        trigger_build(image, tag, message)

    try:
        mc.put_object('trigger', "%s/updated" % image, io.BytesIO(updated_str.encode('utf-8')), len(updated_str.encode('utf-8')))
    except:
        pass

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

    url = "https://github.com/%s/commits/%s.atom" % (RESSOURCES[repository]['repository'], branch)
    response = requests.get(url)
    feed = atoma.parse_atom_bytes(response.content)
    updated = feed.updated

    if updated > last_updated:
        last_entry = feed.entries[0]
        commit = last_entry.links[0].href.split('/')[-1]
        message = "%s (%s, %s)" % (RESSOURCES[repository]['repository'], branch, commit)
        trigger_build(repository, branch, message)

    store = updated.strftime('%Y-%m-%dT%H:%M:%SZ').encode('utf-8')

    try:
        mc.put_object('trigger', "%s/updated" % repository, io.BytesIO(store), len(store))
    except:
        pass


def main():
    for ressource in RESSOURCES:

        if RESSOURCES[ressource]['type'] == 'git':
            print("Checking repository %s @ %s" % (RESSOURCES[ressource]['branch'], RESSOURCES[ressource]['repository']))
            check_repository(ressource, RESSOURCES[ressource]['branch'])
        elif RESSOURCES[ressource]['type'] == 'docker':
            print("Checking image %s @ %s" % (RESSOURCES[ressource]['tag'], RESSOURCES[ressource]['image']))
            check_image(ressource, RESSOURCES[ressource]['tag'])


if __name__ == '__main__':
    main()
