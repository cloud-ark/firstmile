'''
 Copyright (C) Devcentric, Inc - All Rights Reserved
 Unauthorized copying of this file, via any medium is strictly prohibited
 Proprietary and confidential
 Written by Devdatta Kulkarni <devdattakulkarni@gmail.com> January 27, 2017
'''

import os
import subprocess
import pexpect

from testtools import TestCase

from functionaltests import utils

MAX_WAIT_COUNT = 180
SAMPLE_REPO = "https://devdattakulkarni@bitbucket.org/devdattakulkarni/lme-examples.git"
SAMPLE_REPO_NAME = "lme-examples"

class TestGoogle(TestCase):

    @classmethod
    def setUpClass(cls):
        fpath = ("/tmp/{sample_repo_name}").format(sample_repo_name=SAMPLE_REPO_NAME)
        if not os.path.exists(fpath):
            cmd = ("git clone {sample_repo} /tmp/{sample_repo_name}").format(sample_repo=SAMPLE_REPO,
                                                                             sample_repo_name=SAMPLE_REPO_NAME)
            os.system(cmd)


    def test_app_deploy_no_service(self):
        cwd = os.getcwd()
        os.chdir("/tmp/lme-examples/hello-world")
        deploy_cmd = "cld app deploy --cloud google"
        dep_id = ''
        try:
            child = pexpect.spawn(deploy_cmd)
            expected = ">"
            child.expect(expected)
            child.sendline("application.py")
            child.expect(expected)
            child.sendline("5000")
            child.expect(expected)
            child.sendline("abcd-156616")
            lines = child.read()
            dep_id, name = utils.parse_dep_id("google", lines)
        except Exception as e:
            print(e)

        show_cmd = ("cld app show --deploy-id {dep_id}").format(dep_id=dep_id)
        self.assertTrue(utils.assert_deploy_complete(show_cmd, "APP_DEPLOYMENT_COMPLETE"),
                        "App deployment completed")

        os.chdir(cwd)

    def test_app_deploy_with_mysql_service(self):
        cwd = os.getcwd()
        os.chdir("/tmp/lme-examples/greetings-python")
        deploy_cmd = "cld app deploy --cloud google --service-name mysql"
        dep_id = ''
        try:
            child = pexpect.spawn(deploy_cmd)
            expected = ">"
            child.expect(expected)
            child.sendline("application.py")
            child.expect(expected)
            child.sendline("5000")
            child.expect(expected)
            child.sendline("DB")
            child.expect(expected)
            child.sendline("HOST")
            child.expect(expected)
            child.sendline("USER")
            child.expect(expected)
            child.sendline("PASSWORD")
            lines = child.read()
            dep_id, name = utils.parse_dep_id("google", lines)
        except Exception as e:
            print(e)

        show_cmd = ("cld app show --deploy-id {dep_id}").format(dep_id=dep_id)
        self.assertTrue(utils.assert_deploy_complete(show_cmd, "APP_DEPLOYMENT_COMPLETE"),
                        "App deployment completed")

        os.chdir(cwd)

    def test_mysql_instance_provision(self):
        cwd = os.getcwd()
        os.chdir("/tmp/lme-examples/greetings-python")
        deploy_cmd = "cld service provision --cloud google"
        dep_id = ''
        try:
            output = subprocess.Popen(deploy_cmd, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, shell=True).communicate()[0]

            dep_id, name = utils.parse_dep_id("google", output)
        except Exception as e:
            print(e)

        show_cmd = ("cld service show --deploy-id {dep_id}").format(dep_id=dep_id)
        self.assertTrue(utils.assert_deploy_complete(show_cmd, "SERVICE_DEPLOYMENT_COMPLETE"),
                        "Service deployment completed")
        utils.cleanup(name)

        os.chdir(cwd)

