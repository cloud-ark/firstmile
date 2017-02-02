'''
Created on Jan 19, 2017

@author: devdatta
'''
import logging

from cliff.command import Command

import deployment as dp


class AppDelete(Command):
    "Delete an application"

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(AppDelete, self).get_parser(prog_name)
        parser.add_argument('--deploy-id',
                                 dest='deployid',
                                 help="Deployment ID/")
        return parser
    
    def _app_delete(self, deploy_id):
        result = dp.Deployment().delete(deploy_id)
        self.log.debug("App delete result:%s" % result)

    def take_action(self, parsed_args):
        
        if parsed_args.deployid:
            self._app_delete(parsed_args.deployid)
