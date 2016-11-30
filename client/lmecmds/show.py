import logging
import json

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
        return parser

    def take_action(self, parsed_args):
        #self.log.info('Show application info')
        #self.log.debug('Show application info')
        #self.app.stdout.write('Show app info\n')
        #self.app.stdout.write("Passed args:%s" % parsed_args)
        
        if parsed_args.deployid:
            result = dp.Deployment().get(parsed_args.deployid)
            
            status_json = json.loads(result)
            status_val = status_json['app_data']
            
            self.app.stdout.write("App status:%s\n" % status_val)