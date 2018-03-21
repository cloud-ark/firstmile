import logging
import prettytable

from cliff.command import Command

import common
import deployment as dp


class AppLogs(Command):
    "Retrieve application deployment and runtime logs"

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(AppLogs, self).get_parser(prog_name)
        parser.add_argument('--deploy-id',
                                 dest='deployid',
                                 help="Deployment ID")
        return parser
    
    def _app_logs(self, deploy_id):
        result = dp.Deployment().logs(deploy_id)
        x = prettytable.PrettyTable()
        x.field_names = ["App Name", "App Version", "Cloud", "Log location"]
        if result:
            pretty_table = common.artifact_logs_show(result, x)
            self.app.stdout.write("%s\n" % pretty_table)

    def take_action(self, parsed_args):

        dest = parsed_args.deployid
        if not dest:
            dest = raw_input("Please enter deploy id>")
        self._app_logs(dest)
