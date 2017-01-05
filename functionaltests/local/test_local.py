'''
Created on Jan 4, 2017

@author: devdatta
'''
import os
import subprocess
import pexpect
import time

from testtools import TestCase

MAX_WAIT_COUNT = 60
SAMPLE_REPO = "https://devdattakulkarni@bitbucket.org/devdattakulkarni/lme-examples.git"
SAMPLE_REPO_NAME = "lme-examples"

class TestLocal(TestCase):

    @classmethod
    def setUpClass(cls):
        fpath = ("/tmp/{sample_repo_name}").format(sample_repo_name=SAMPLE_REPO_NAME)
        if not os.path.exists(fpath):
            cmd = ("git clone {sample_repo} /tmp/{sample_repo_name}").format(sample_repo=SAMPLE_REPO,
                                                                             sample_repo_name=SAMPLE_REPO_NAME)
            os.system(cmd)

    def _parse_dep_id(self, cloud, lines):
        print("Lines:%s" % lines)
        for line in lines.split("\n"):
            print("Line:%s" % line)
            parts = line.split("|")
            parts = [item.rstrip() for item in parts]
            parts = [item.lstrip() for item in parts]
            if parts and cloud in parts:
                name = parts[1].rstrip().lstrip()
                dep_id = parts[2].rstrip().lstrip()
                print("Dep id:%s Name:%s" % (dep_id, name))
                return dep_id, name

    def _assert_deploy_complete(self, show_cmd, status):
        count = 0
        while count < MAX_WAIT_COUNT:
            try:
                output = subprocess.Popen(show_cmd,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE,
                                          shell=True).communicate()[0]
                print("Show output:%s" % output)
            except Exception as e:
                print(e)

            for line in output.split("\n"):
                parts = line.split(" ")
                if status in parts:
                    return True

            count = count + 1
            time.sleep(1)
        return False

    def _cleanup(self, name):
        cmd = ("docker ps | grep {name} | head -1 | awk '{{print $1}}' | xargs docker stop").format(name=name)
        os.system(cmd)
        
        cmd = ("docker images | grep {name} | head -1 | awk '{{print $3}}' | xargs docker rmi -f").format(name=name)
        os.system(cmd)
        
        cmd = ("docker ps -a | grep {name} | head -1 | awk '{{print $1}}' | xargs docker rm").format(name=name)
        os.system(cmd)

    def test_with_flags_no_service(self):
        cwd = os.getcwd()
        os.chdir("/tmp/lme-examples/hello-world")
        deploy_cmd = "lme app deploy --cloud local"
        dep_id = ''
        try:
            child = pexpect.spawn(deploy_cmd)
            expected = ">"
            child.expect(expected)
            child.sendline("application.py")
            lines = child.read()
            dep_id, name = self._parse_dep_id("local", lines)
        except Exception as e:
            print(e)

        show_cmd = ("lme app show --deploy-id {dep_id}").format(dep_id=dep_id)
        self.assertTrue(self._assert_deploy_complete(show_cmd, "APP_DEPLOYMENT_COMPLETE"),
                        "App deployment completed")
        self._cleanup(name)

        os.chdir(cwd)

    def test_mysql_instance_deploy(self):
        cwd = os.getcwd()
        os.chdir("/tmp/lme-examples/greetings-python")
        deploy_cmd = "lme service deploy --cloud local"
        dep_id = ''
        try:
            output = subprocess.Popen(deploy_cmd, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, shell=True).communicate()[0]

            dep_id, name = self._parse_dep_id("local", output)
        except Exception as e:
            print(e)

        show_cmd = ("lme service show --deploy-id {dep_id}").format(dep_id=dep_id)
        self.assertTrue(self._assert_deploy_complete(show_cmd, "SERVICE_DEPLOYMENT_COMPLETE"),
                        "Service deployment completed")
        self._cleanup(name)

        os.chdir(cwd)