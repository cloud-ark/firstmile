'''
 Copyright (C) Devcentric, Inc - All Rights Reserved
 Unauthorized copying of this file, via any medium is strictly prohibited
 Proprietary and confidential
 Written by Devdatta Kulkarni <devdattakulkarni@gmail.com> January 19, 2017
'''

import logging

from cliff.command import Command

import deployment as dp


class AppDelete(Command):
    "Delete application"

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(AppDelete, self).get_parser(prog_name)
        parser.add_argument('--deploy-id',
                                 dest='deployid',
                                 help="Application Deployment ID")
        return parser
    
    def _app_delete(self, deploy_id):
        result = dp.Deployment().delete(deploy_id)
        self.log.debug("App delete result:%s" % result)

    def take_action(self, parsed_args):

        dest = parsed_args.deployid
        if not dest:
            dest = raw_input("Please enter deploy id>")
        self._app_delete(dest)