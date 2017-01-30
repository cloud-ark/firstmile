'''
Created on Jan 28, 2017

@author: devdatta
'''
import logging
import prettytable

from cliff.command import Command

import deployment as dp
import common


class ServiceList(Command):
    "List service instances"

    log = logging.getLogger(__name__)
    
    def _service_list(self):
        result = dp.Deployment().get_all_services()
        x = prettytable.PrettyTable()
        x.field_names = ["Deploy ID", "Service Name", "Service Version", "Cloud"]

        if result:
            pretty_table = common.artifact_list_show(result, x)

        self.app.stdout.write("%s\n" % pretty_table)

    def take_action(self, parsed_args):
        self._service_list()