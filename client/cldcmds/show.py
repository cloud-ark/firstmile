''' 
 Copyright (C) Devcentric, Inc - All Rights Reserved
 Unauthorized copying of this file, via any medium is strictly prohibited
 Proprietary and confidential
 Written by Devdatta Kulkarni <devdattakulkarni@gmail.com>
'''

import logging
import json
import prettytable

from cliff.command import Command

import deployment as dp
import common


class Show(Command):
    "Display application information"

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(Show, self).get_parser(prog_name)
        parser.add_argument('--deploy-id',
                                 dest='deployid',
                                 help="Deployment ID")
        parser.add_argument('--app-name',
                                 dest='appname',
                                 help="Name of the application")
        parser.add_argument('--cloud',
                                 dest='cloud',
                                 help="Name of the cloud")
        return parser

    def _app_name_show(self, appname):
        result = dp.Deployment().get_app_info(appname)
        x = prettytable.PrettyTable()
        x.field_names = ["Deploy ID", "App Version", "Cloud", "Status", "App Info"]

        if result:
            pretty_table = common.artifact_name_show(result, x)

        self.app.stdout.write("%s\n" % pretty_table)

    def _deployid_show(self, dep_id):
        result = dp.Deployment().get(dep_id)
        x = prettytable.PrettyTable()
        x.field_names = ["App Name", "App Version", "Cloud", "Status", "App Info"]

        if result:
            pretty_table = common.artifact_depid_show(result, x)

        self.app.stdout.write("%s\n" % pretty_table)

    def _cloud_show(self, cloud):
        result = dp.Deployment().get_cloud_info(cloud)
        x = prettytable.PrettyTable()
        x.field_names = ["Deploy ID", "App Name", "App Version", "App URL"]
        if result:
            status_json = json.loads(result)
            app_status_list = status_json['app_data']

            logging.debug(app_status_list)

            for line in app_status_list:
                dep_id = line['dep_id']
                app_name = line['app_name']
                version = line['app_version']
                app_url = line['url']

                row = [dep_id, app_name, version, app_url]
                x.add_row(row)

        self.app.stdout.write("%s\n" % x)

    def _deploy_id_show_bak(self, deploy_id):
        if deploy_id:
            result = dp.Deployment().get(deploy_id)

            status_json = json.loads(result)
            status_val = status_json['app_data']

            status_val_list = status_val.split(',')

            x = prettytable.PrettyTable()
            x.field_names = ["App Name", "Deploy ID", "Status", "Cloud", "App URL"]

            app_name = ''
            app_deploy_id = deploy_id
            app_deploy_time = ''
            app_status = ''
            app_url = ''
            cloud = ''
            for stat in status_val_list:
                stat = stat.rstrip().lstrip()
                if stat.lower().find("name::") >= 0:
                    l = stat.split("::")
                    app_name = l[2]
                elif stat.lower().find("deploy_id::") >= 0:
                    l = stat.split("::")
                    app_deploy_id = l[1]
                elif stat.lower().find("cloud::") >= 0:
                    l = stat.split("::")
                    cloud = l[2]
                elif stat.lower().find("status::") >= 0:
                    l = stat.split("::")
                    app_status = l[1]
                elif stat.lower().find("url::") >= 0:
                    l = stat.split("::")
                    app_url = l[1]

            row = [app_name, app_deploy_id, app_status, cloud, app_url]
            x.add_row(row)
            self.app.stdout.write("%s\n" % x)

    def take_action(self, parsed_args):

        if parsed_args.appname:
            self._app_name_show(parsed_args.appname)

        if parsed_args.cloud:
            self._cloud_show(parsed_args.cloud)

        if parsed_args.deployid:
            self._deployid_show(parsed_args.deployid)