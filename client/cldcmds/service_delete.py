'''
 Copyright (C) Devcentric, Inc - All Rights Reserved
 Unauthorized copying of this file, via any medium is strictly prohibited
 Proprietary and confidential
 Written by Devdatta Kulkarni <devdattakulkarni@gmail.com> April 03, 2017
'''
import logging

from cliff.command import Command

import deployment as dp


class ServiceDelete(Command):
    "Delete service instance"

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(ServiceDelete, self).get_parser(prog_name)
        parser.add_argument('--deploy-id',
                                 dest='deployid',
                                 help="Service Deployment ID")
        return parser
    
    def _service_delete(self, deploy_id):
        result = dp.Deployment().service_delete(deploy_id)
        self.log.debug("Service delete result:%s" % result)

    def take_action(self, parsed_args):

        dest = parsed_args.deployid
        if not dest:
            dest = raw_input("Please enter deploy id>")
        self._service_delete(dest)

