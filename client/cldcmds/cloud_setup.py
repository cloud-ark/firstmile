'''
 Copyright (C) Devcentric, Inc - All Rights Reserved
 Unauthorized copying of this file, via any medium is strictly prohibited
 Proprietary and confidential
 Written by Devdatta Kulkarni <devdattakulkarni@gmail.com> March 1, 2017
'''

from cliff.command import Command

import common

class CloudSetup(Command):
    "Setup cloud"

    def get_parser(self, prog_name):
        parser = super(CloudSetup, self).get_parser(prog_name)
        parser.add_argument('--cloud',
                                 dest='cloud',
                                 help="Name of the cloud (google/aws/local-docker)")
        return parser

    def _setup_google(self):
        common.setup_google()

    def _setup_aws(self):
        common.setup_aws()

    def take_action(self, parsed_args):
        if parsed_args.cloud == 'google':
            self._setup_google()
        if parsed_args.cloud == 'aws':
            self._setup_aws()
    