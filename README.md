# travis-trigger

[![Build Status](https://travis-ci.org/osism/travis-trigger.svg?branch=master)](https://travis-ci.org/osism/travis-trigger)

This script gets the latest commit Atom feed from Github for a set of defined repositories.
If a commit has been added since the last execution, a build on a definable repository is
triggered on Travis. The timestamp of the last change is saved on a Minio server.

We use this script to trigger a rebuild of our Docker images when changes are made in
upstream projects. This enables us to provide up-to-date images in a timely manner.

The following repositories are being monitored for changes.

| Repository              | Branches                                  | Target repository          |
|-------------------------|-------------------------------------------|----------------------------|
| ceph/ceph-ansible       | stable-3.2                                | osism/docker-ceph-ansible  |
| openstack/kolla-ansible | stable/queens, stable/rocky, stable/stein | osism/docker-kolla-ansible |

License
-------

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Author information
------------------

This script was created by [Betacloud Solutions GmbH](https://betacloud-solutions.de).
