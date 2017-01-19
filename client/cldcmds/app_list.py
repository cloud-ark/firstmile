'''
Created on Jan 19, 2017

@author: devdatta
'''
import logging
import prettytable

from cliff.command import Command

import deployment as dp
import common


class AppList(Command):
    "List applications"

    log = logging.getLogger(__name__)
    
    def _app_list(self):
        result = dp.Deployment().get_all_apps()
        x = prettytable.PrettyTable()
        x.field_names = ["Deploy ID", "App Name", "App Version", "Cloud"]

        if result:
            pretty_table = common.artifact_list_show(result, x)

        self.app.stdout.write("%s\n" % pretty_table)

    def take_action(self, parsed_args):
        self._app_list()



