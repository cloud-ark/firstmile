'''
Created on Jan 27, 2017

@author: devdatta
'''
import os
import subprocess
import pexpect

from testtools import TestCase

from functionaltests import utils

MAX_WAIT_COUNT = 300
SAMPLE_REPO = "https://devdattakulkarni@bitbucket.org/devdattakulkarni/lme-examples.git"
SAMPLE_REPO_NAME = "lme-examples"

class TestAWS(TestCase):

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
        deploy_cmd = "cld app deploy --cloud aws"
        dep_id = ''
        try:
            child = pexpect.spawn(deploy_cmd)
            expected = ">"
            child.expect(expected)
            child.sendline("application.py")
            child.expect(expected)
            child.sendline("5000")
            lines = child.read()
            dep_id, name = utils.parse_dep_id("aws", lines)
        except Exception as e:
            print(e)

        show_cmd = ("cld app show --deploy-id {dep_id}").format(dep_id=dep_id)
        self.assertTrue(utils.assert_deploy_complete(show_cmd, "APP_DEPLOYMENT_COMPLETE",
                                                     wait_count=MAX_WAIT_COUNT),
                        "App deployment completed")
        utils.cleanup(name)
        os.chdir(cwd)

    def test_app_deploy_with_mysql_service(self):
        cwd = os.getcwd()
        os.chdir("/tmp/lme-examples/greetings-python")
        deploy_cmd = "cld app deploy --cloud aws --service-name mysql"
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
            dep_id, name = utils.parse_dep_id("aws", lines)
        except Exception as e:
            print(e)

        show_cmd = ("cld app show --deploy-id {dep_id}").format(dep_id=dep_id)
        self.assertTrue(utils.assert_deploy_complete(show_cmd, "APP_DEPLOYMENT_COMPLETE",
                                                     wait_count=900),
                        "App deployment completed")

        utils.cleanup(name)
        os.chdir(cwd)

    def test_mysql_instance_provision(self):
        cwd = os.getcwd()
        os.chdir("/tmp/lme-examples/greetings-python")
        deploy_cmd = "cld service provision --cloud aws"
        dep_id = ''
        try:
            output = subprocess.Popen(deploy_cmd, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, shell=True).communicate()[0]

            dep_id, name = utils.parse_dep_id("aws", output)
        except Exception as e:
            print(e)

        show_cmd = ("cld service show --deploy-id {dep_id}").format(dep_id=dep_id)
        self.assertTrue(utils.assert_deploy_complete(show_cmd, "SERVICE_DEPLOYMENT_COMPLETE",
                                                     wait_count=MAX_WAIT_COUNT),
                        "Service deployment completed")
        utils.cleanup(name)

        os.chdir(cwd)
