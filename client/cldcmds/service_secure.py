'''
 Copyright (C) Devcentric, Inc - All Rights Reserved
 Unauthorized copying of this file, via any medium is strictly prohibited
 Proprietary and confidential
 Written by Devdatta Kulkarni <devdattakulkarni@gmail.com> April 11, 2017
'''
import logging

from cliff.command import Command

import deployment as dp


class ServiceSecure(Command):
    "Secure service instance"

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(ServiceSecure, self).get_parser(prog_name)
        parser.add_argument('--deploy-id',
                                 dest='deployid',
                                 help="Service Deployment ID")
        return parser
    
    def _service_secure(self, deploy_id):
        result = dp.Deployment().service_secure(deploy_id)
        self.log.debug("Service secure result:%s" % result)

    def take_action(self, parsed_args):

        dest = parsed_args.deployid
        if not dest:
            dest = raw_input("Please enter deploy id>")
        self._service_secure(dest)
