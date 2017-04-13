'''
 Copyright (C) Devcentric, Inc - All Rights Reserved
 Unauthorized copying of this file, via any medium is strictly prohibited
 Proprietary and confidential
 Written by Devdatta Kulkarni <devdattakulkarni@gmail.com> March 28, 2017
'''
import logging
import common

from cliff.command import Command


class FirstMileLogs(Command):
    "Retrieve FirstMile sandbox logs"

    log = logging.getLogger(__name__)
    
    def _extract_logs(self):
        cmd = "sudo docker ps -a | grep firstmile | head -1 | awk '{print $1}'"
        err, output = common.execute_shell_cmd(cmd)
        if output:
            output = output.rstrip().lstrip()
            cp_cmd = ("sudo docker cp {cont_id}:/src/cld.log firstmile.log").format(cont_id=output)
            err, op = common.execute_shell_cmd(cp_cmd)
            
            if not err:
                print("FirstMile logs saved in firstmile.log")

    def take_action(self, parsed_args):
        self._extract_logs()


class FirstMileRestart(Command):
    "Display steps to restart FirstMile sandbox"

    log = logging.getLogger(__name__)
    
    def _restart(self):
        print("===============================================================================================================================")
        print("Go to the directory where you downloaded firstmile and then run following commands:")
        print("sudo docker build -t firstmile-img .")
        print("sudo docker run -u ubuntu -p 5002:5002 -v /var/run/docker.sock:/var/run/docker.sock -v $HOME:/home/ubuntu -d firstmile-img")
        print("===============================================================================================================================")

    def take_action(self, parsed_args):
        self._restart()


class FirstMileCleanup(Command):
    "Display steps to cleanup FirstMile workspace"
    
    def _cleanup(self):
        print("===============================================================================================================================")
        print("FirstMile server uses ~/.cld/data/deployments as workspace folder for all deployments.")
        print("- Any application that is deployed using FirstMile is stored in a directory inside this folder.")
        print("- Services provisioned using FirstMile are stored in services folder inside this folder.")
        print("You can delete application folders or service folders to cleanup the workspace.")
        print("You can also delete the entire workspace. If you do that you will have to then run 'cld cloud setup' to get your cloud-specific setup.")
        print("===============================================================================================================================")

    def take_action(self, parsed_args):
        self._cleanup()
        