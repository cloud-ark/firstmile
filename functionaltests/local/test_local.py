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

    @classmethod
    def tearDownClass(cls):
        fpath = ("/tmp/{sample_repo_name}").format(sample_repo_name=SAMPLE_REPO_NAME)
        if os.path.exists(fpath):
            cmd = ("rm -rf /tmp/{sample_repo_name}").format(sample_repo_name=SAMPLE_REPO_NAME)
            os.system(cmd)

    def _parse_dep_id(self, cloud, lines):
        for line in lines.split("\n"):
            parts = line.split(" ")
            if cloud in parts:
                dep_id = parts[6]
                name = parts[1]
                return dep_id, name

    def _assert_deploy_complete(self, show_cmd):
        count = 0
        while count < MAX_WAIT_COUNT:
            try:
                output = subprocess.Popen(show_cmd,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE,
                                          shell=True).communicate()[0]
            except Exception as e:
                print(e)

            for line in output.split("\n"):
                parts = line.split(" ")
                if 'DEPLOYMENT_COMPLETE' in parts:
                    return True

            count = count + 1
            time.sleep(1)
        return False

    def _cleanup(self, name):
        cmd = ("docker ps | grep {name} | head -1 | awk '{{print $1}}' | xargs docker stop").format(name=name)
        os.system(cmd)
        
        cmd = ("docker images | grep {name} | head -1 | awk '{{print $1}}' | xargs docker rmi -f").format(name=name)
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
        self.assertTrue(self._assert_deploy_complete(show_cmd), "App deployment completed")

        self._cleanup(name)

        os.chdir(cwd)