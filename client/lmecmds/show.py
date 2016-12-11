import logging
import json
import prettytable

from cliff.command import Command

import deployment as dp


class Show(Command):
    "Show application status"

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(Show, self).get_parser(prog_name)
        parser.add_argument('--deploy-id',
                                 dest='deployid',
                                 help="Deployment ID/URL")
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
        x.field_names = ["Deploy ID", "App Version", "Cloud", "App URL"]
        if result:
            status_json = json.loads(result)
            app_status_list = status_json['app_data']

            logging.debug(app_status_list)


            for line in app_status_list:
                dep_id = line['dep_id']
                version = line['app_version']
                cloud = line['cloud']
                app_url = line['url']

                row = [dep_id, version, cloud, app_url]
                x.add_row(row)

        self.app.stdout.write("%s\n" % x)

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

    def take_action(self, parsed_args):
        #self.log.info('Show application info')
        #self.log.debug('Show application info')
        #self.app.stdout.write('Show app info\n')
        #self.app.stdout.write("Passed args:%s" % parsed_args)

        if parsed_args.appname:
            self._app_name_show(parsed_args.appname)

        if parsed_args.cloud:
            self._cloud_show(parsed_args.cloud)

        if parsed_args.deployid:
            result = dp.Deployment().get(parsed_args.deployid)

            status_json = json.loads(result)
            status_val = status_json['app_data']

            status_val_list = status_val.split(',')

            x = prettytable.PrettyTable()
            x.field_names = ["App Name", "Deploy ID", "Status", "Cloud", "App URL"]

            app_name = ''
            app_deploy_id = parsed_args.deployid
            app_deploy_time = ''
            app_status = ''
            app_url = ''
            cloud = ''
            for stat in status_val_list:
                stat = stat.rstrip().lstrip()
                if stat.lower().find("name::") >= 0:
                    l = stat.split("::")
                    app_name = l[1]
                elif stat.lower().find("deploy_id::") >= 0:
                    l = stat.split("::")
                    app_deploy_id = l[1]
                elif stat.lower().find("cloud::") >= 0:
                    l = stat.split("::")
                    cloud = l[1]
                elif stat.lower().find("status::") >= 0:
                    l = stat.split("::")
                    app_status = l[1]
                elif stat.lower().find("url::") >= 0:
                    l = stat.split("::")
                    app_url = l[1]

            row = [app_name, app_deploy_id, app_status, cloud, app_url]
            x.add_row(row)
            self.app.stdout.write("%s\n" % x)