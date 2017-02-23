# Copyright 2016 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import amulet
import json
import subprocess
import time


import charmhelpers.contrib.openstack.amulet.deployment as amulet_deployment
import charmhelpers.contrib.openstack.amulet.utils as os_amulet_utils

# Use DEBUG to turn on debug logging
u = os_amulet_utils.OpenStackAmuletUtils(os_amulet_utils.DEBUG)


class ManilaPluginCharmDeployment(amulet_deployment.OpenStackAmuletDeployment):
    """Amulet tests on a basic manila plugin charm deployment."""

    def __init__(self, series, openstack=None, source=None, stable=False):
        """Deploy the entire test environment."""
        super(ManilaPluginCharmDeployment, self).__init__(
            series, openstack, source, stable)
        self._add_services()
        self._add_relations()
        self._configure_services()
        self._deploy()

        u.log.info('Waiting on extended status checks...')
        exclude_services = ['mysql', ]
        self._auto_wait_for_status(exclude_services=exclude_services)

        self._initialize_tests()

    def _add_services(self):
        """Add services

           Add the services that we're testing, where manila plugin is a
           subordinate to the manila charm, and is deployed locally, whereas
           the rest of the services are from lp branches that are
           compatible with the local charm (e.g. stable or next).
           """
        this_service = {'name': '{{ metadata.package }}'}
        other_services = [
            {'name': 'mysql',
             'location': 'cs:percona-cluster',
             'constraints': {'mem': '3072M'}},
            {'name': 'rabbitmq-server'},
            {'name': 'keystone'},
            {'name': 'manila'}
        ]
        super(ManilaPluginCharmDeployment, self)._add_services(
            this_service, other_services)

    def _add_relations(self):
        """Add all of the relations for the services."""
        relations = {
            'manila:shared-db': 'mysql:shared-db',
            'manila:amqp': 'rabbitmq-server:amqp',
            'manila:identity-service': 'keystone:identity-service',
            'manila:manila-plugin': '{{ metadata.package }}:manila-plugin',
            'keystone:shared-db': 'mysql:shared-db',
        }
        super(ManilaPluginCharmDeployment, self)._add_relations(relations)

    def _configure_services(self):
        """Configure all of the services."""
        keystone_config = {
            'admin-password': 'openstack',
            'admin-token': 'ubuntutesting',
        }
        manila_config = {
            'default-share-backend': 'generic',
        }
        manila_generic_config = {
            'driver-handles-share-servers': False,
        }
        configs = {
            'keystone': keystone_config,
            'manila': manila_config,
            'manila-generic': manila_generic_config,
        }
        super(ManilaPluginCharmDeployment, self)._configure_services(configs)

    def _get_token(self):
        return self.keystone.service_catalog.catalog['token']['id']

    def _initialize_tests(self):
        """Perform final initialization before tests get run."""
        # Access the sentries for inspecting service units
        self.manila_sentry = self.d.sentry['manila'][0]
        self.manila_plugin_sentry = self.d.sentry['{{ metadata.package }}'][0]
        self.mysql_sentry = self.d.sentry['mysql'][0]
        self.keystone_sentry = self.d.sentry['keystone'][0]
        self.rabbitmq_sentry = self.d.sentry['rabbitmq-server'][0]

        u.log.debug('openstack release val: {}'.format(
            self._get_openstack_release()))
        u.log.debug('openstack release str: {}'.format(
            self._get_openstack_release_string()))

        # Authenticate admin with keystone endpoint
        self.keystone = u.authenticate_keystone_admin(self.keystone_sentry,
                                                      user='admin',
                                                      password='openstack',
                                                      tenant='admin')

    def check_and_wait(self, check_command, interval=2, max_wait=200,
                       desc=None):
        waited = 0
        while not check_command() or waited > max_wait:
            if desc:
                u.log.debug(desc)
            time.sleep(interval)
            waited = waited + interval
        if waited > max_wait:
            raise Exception('cmd failed {}'.format(check_command))

    def _run_action(self, unit_id, action, *args):
        command = ["juju", "action", "do", "--format=json", unit_id, action]
        command.extend(args)
        print("Running command: %s\n" % " ".join(command))
        output = subprocess.check_output(command)
        output_json = output.decode(encoding="UTF-8")
        data = json.loads(output_json)
        action_id = data[u'Action queued with id']
        return action_id

    def _wait_on_action(self, action_id):
        command = ["juju", "action", "fetch", "--format=json", action_id]
        while True:
            try:
                output = subprocess.check_output(command)
            except Exception as e:
                print(e)
                return False
            output_json = output.decode(encoding="UTF-8")
            data = json.loads(output_json)
            if data[u"status"] == "completed":
                return True
            elif data[u"status"] == "failed":
                return False
            time.sleep(2)

    def test_205_manila_to_manila_plugin(self):
        """Verify that the manila to {{ metadata.package }}
        config is working"""
        u.log.debug("Checking the manila:{{ metadata.package }}"
                    " relation data...")
        manila = self.manila_sentry
        relation = ['manila-plugin',
                    '{{ metadata.package }}:manila-plugin']
        expected = {
            'private-address': u.valid_ip,
            '_authentication_data': u.not_null,
        }
        ret = u.validate_relation_data(manila, relation, expected)
        if ret:
            message = u.relation_error('manila {{ metadata.package }}', ret)
            amulet.raise_status(amulet.FAIL, msg=message)
        u.log.debug('OK')

    def test_206_manila_plugin_to_manila(self):
        """Verify that the {{ metadata.package }}
        to manila config is working"""
        u.log.debug("Checking the {{ metadata.package }}:"
                    "manila relation data...")
        manila_generic = self.manila_generic_sentry
        relation = ['manila-plugin', 'manila:manila-plugin']
        expected = {
            'private-address': u.valid_ip,
            '_configuration_data': u.not_null,
            '_name': 'generic'
        }
        ret = u.validate_relation_data(manila_generic, relation, expected)
        if ret:
            message = u.relation_error('manila {{ metadata.package }}', ret)
            amulet.raise_status(amulet.FAIL, msg=message)
        u.log.debug('OK')
