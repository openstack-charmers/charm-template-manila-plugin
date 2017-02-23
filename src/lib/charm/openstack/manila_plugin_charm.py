import socket
import subprocess

import charmhelpers.core.hookenv as hookenv
import charmhelpers.contrib.network.ip as ch_ip
import charms_openstack.charm
import charms_openstack.adapters


MANILA_DIR = '/etc/manila/'
MANILA_CONF = MANILA_DIR + "manila.conf"

# select the default release function and ssl feature
charms_openstack.charm.use_defaults('charm.default-select-release')


###
# Compute an option to help with template rendering
@charms_openstack.adapters.config_property
def computed_some_property(config):
    """Compute and return some property from the config options.

    Use in a template as config. {{ '{{' }} config.computed_some_property {{ '}}' }}

    :returns: something
    """
    return config.something + 10


class {{ charm_class }}(charms_openstack.charm.OpenStackCharm):

    # Internal name of charm
    service_name = name = '{{ metadata.package }}'

    # First release supported
    release = '{{ release }}'

    # List of packages to install for this charm
    packages = {{ packages_list }}

    # This is needed to enable the versioning code to pick out a version
    version_package = '{{ version_package }}'

    # There is no service in this charm
    service_type = None

    # There is no service for this charm.
    default_service = None
    services = []

    required_relations = []

    # Generally, there is no service that a config charm looks after
    restart_map = {}

    # Generally, there is no database to sync.
    sync_cmd = []

    def install(self):
        """Called when the charm is being installed or upgraded.

        The available configuration options need to be check AFTER the charm is
        installed to check to see whether it is blocked or can go into service.

        Use this function if the charm needs to do something other that install
        the packages from a defined archive.  Delete this function if only the
        standard functionality is needed.
        """
        # This installs the packages defined in self.packages
        super().install()
        # Do any other installation work that is needed.  If a license key is
        # required then use the custom_assess_status_check() function below to
        # determine whether it is needed.
        # This assess_status() will determine what status the charm is at after
        # install.
        self.assess_status()

    def custom_assess_status_check(self):
        """Validate that the driver configuration is sane/complete

        Return (status, message) if there is a problem or
               (None, None) if there are no issues.

        Delete this function if it's not needed.
        """
        options = self.options
        # can check options.thing to ensure that it makes sense
        # if wrong return 'blocked', "The driver is badly configured ..."
        return None, None

    def get_config_for_principal(self, auth_data):
        """Assuming that the configuration data is valid, return the
        configuration data for the principal charm.

        The format of the complete returned data is:
        {
            "<config file>: <string>
        }

        If the configuration is not complete, or we don't have auth data from
        the principal charm, then we return and emtpy dictionary {}

        Almost no plugins, other that the generic plugin, need the auth data so
        it can be ignored.

        :param auth_data: the raw dictionary received from the principal charm
        :returns: structure described above.
        """
        # If there is no auth_data yet, then we can't write our config.
        if not auth_data:
            return {}
        # If the state from the assess_status is not None then we're blocked,
        # so don't send any config to the principal.
        state, message = self.custom_assess_status_check()
        if state:
            return {}

        # Do any further checking on options that might be needed?
        options = self.options  # tiny optimisation for less typing.

        if not options.some_option:
            return {}

        # We have the config that is reasonably sensible.
        # We can now render the config file segment.
        manila_plugin = charms.reactive.RelationBase.from_state(
            'manila-plugin.available')
        self.adapters_instance.add_relation(manila_plugin)
        # Render the config files needed.  Here it's just MANILA_CONF
        # Change the template as needed for the configuration.
        rendered_configs = charmhelpers.core.templating.render(
            source=os.path.basename(MANILA_CONF),
            template_loader=os_templating.get_loader(
                'templates/', self.release),
            target=None,
            context=self.adapters_instance)

        return {
            MANILA_CONF: rendered_configs
        }
