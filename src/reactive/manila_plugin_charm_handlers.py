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

import charms_openstack.charm as charm
import charms.reactive as reactive

# This charm's library contains all of the handler code associated with
# sdn_charm
import charm.openstack.{{ charm_lib }}  # noqa

charm.use_defaults(
    'charm.installed',
    'update-status')


@charms.reactive.when('manila-plugin.available')
@charms.reactive.when_not('config.changed')
def send_config(manila_plugin):
    """Send the configuration over to the prinicpal charm"""
    with charms_openstack.charm.provide_charm_instance() as plugin_charm:
        # set the name of the backend using the configuration option
        manila_plugin.name = plugin_charm.options.share_backend_name
        # Set the configuration data for the principal charm.
        manila_plugin.configuration_data = (
            plugin_charm.get_config_for_principal(
                manila_plugin.authentication_data))
        plugin_charm.assess_status()


@charms.reactive.when('manila-plugin.available',
                      'config.changed')
def update_config(manila_plugin):
    send_config(manila_plugin)
