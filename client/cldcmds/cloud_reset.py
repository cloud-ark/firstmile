'''
Created on Jan 23, 2017

@author: devdatta
'''

from cliff.command import Command

import common

class CloudReset(Command):
    "Reset cloud setup"
    
    def get_parser(self, prog_name):
        parser = super(CloudReset, self).get_parser(prog_name)
        parser.add_argument('--cloud',
                                 dest='cloud',
                                 help="Name of the cloud (google/aws/local-docker)")
        return parser

    def _reset_google(self):
        common.reset_google()

    def take_action(self, parsed_args):
        if parsed_args.cloud == 'google':
            self._reset_google()
    