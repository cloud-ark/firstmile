'''
Created on Jan 4, 2017

@author: devdatta
'''
import pexpect
import os
import subprocess
import requests

from testtools import TestCase

from functionaltests import utils

MAX_WAIT_COUNT = 180
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

    def _provision_mysql_instance(self):
        os.chdir("/tmp/lme-examples/greetings-python")
        deploy_cmd = "cld service provision --cloud local-docker"
        dep_id = ''
        try:
            output = subprocess.Popen(deploy_cmd, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, shell=True).communicate()[0]

            dep_id, name = utils.parse_dep_id("local-docker", output)
        except Exception as e:
            print(e)

        return dep_id, name

    def test_app_deploy_no_service(self):
        cwd = os.getcwd()
        os.chdir("/tmp/lme-examples/hello-world")
        deploy_cmd = "cld app deploy --cloud local-docker"
        dep_id = ''
        try:
            child = pexpect.spawn(deploy_cmd)
            expected = ">"
            child.expect(expected)
            child.sendline("application.py")
            child.expect(expected)
            child.sendline("5000")
            lines = child.read()
            dep_id, name = utils.parse_dep_id("local-docker", lines)
        except Exception as e:
            print(e)

        show_cmd = ("cld app show --deploy-id {dep_id}").format(dep_id=dep_id)
        self.assertTrue(utils.assert_deploy_complete(show_cmd, "APP_DEPLOYMENT_COMPLETE"),
                        "App deployment completed")
        utils.cleanup(name)

        os.chdir(cwd)

    def test_app_deploy_with_mysql_service(self):
        cwd = os.getcwd()
        os.chdir("/tmp/lme-examples/greetings-python")
        deploy_cmd = "cld app deploy --cloud local-docker --service-name mysql"
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
            dep_id, name = utils.parse_dep_id("local-docker", lines)
        except Exception as e:
            print(e)

        show_cmd = ("cld app show --deploy-id {dep_id}").format(dep_id=dep_id)
        self.assertTrue(utils.assert_deploy_complete(show_cmd, "APP_DEPLOYMENT_COMPLETE"),
                        "App deployment completed")
        utils.cleanup(name)

        os.chdir(cwd)

    def test_app_deploy_with_yaml_file(self):
        cwd = os.getcwd()
        dep_id, service_name = self._provision_mysql_instance()

        show_cmd = ("cld service show --deploy-id {dep_id}").format(dep_id=dep_id)

        self.assertTrue(utils.assert_deploy_complete(show_cmd, "SERVICE_DEPLOYMENT_COMPLETE"),
                        "Service deployment completed")
        try:
            output = subprocess.Popen(show_cmd, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, shell=True).communicate()[0]
        except Exception as e:
            print(e)

        host, db_name, user, password = utils.parse_service_info(output)

        env_vars_dict = dict()
        env_vars_dict['DB'] = db_name
        env_vars_dict['HOST'] = host
        env_vars_dict['USER'] = user
        env_vars_dict['PASSWORD'] = password

        app_details_dict = {}
        app_details_dict['type'] = 'python'
        app_details_dict['entry_point'] = 'application.py'
        app_details_dict['app_port'] = '5000'
        app_details_dict['env_variables'] = env_vars_dict
        app_dict = {}
        app_dict['application'] = app_details_dict

        cloud_details_dict = {}
        cloud_details_dict['type'] = 'local-docker'
        cloud_dict = {}
        cloud_dict['cloud'] = cloud_details_dict

        list_of_dicts = list()
        list_of_dicts.append(app_dict)
        list_of_dicts.append(cloud_dict)

        target_dir = "/tmp/lme-examples/greetings-python"
        utils.create_cld_yaml_file(target_dir, list_of_dicts)

        deploy_cmd = "cld app deploy --cloud local-docker"
        dep_id = ''
        try:
            output = subprocess.Popen(deploy_cmd, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, shell=True).communicate()[0]
            dep_id, app_name = utils.parse_dep_id("local-docker", output)
        except Exception as e:
            print(e)

        show_cmd = ("cld app show --deploy-id {dep_id}").format(dep_id=dep_id)
        self.assertTrue(utils.assert_deploy_complete(show_cmd, "APP_DEPLOYMENT_COMPLETE"),
                        "App deployment completed")

        try:
            output = subprocess.Popen(show_cmd, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, shell=True).communicate()[0]
            app_url = utils.parse_app_url(output)
        except Exception as e:
            print(e)

        req = requests.get(app_url)
        response = req.text
        self.assertTrue(utils.contains("Hello, World!", response))

        utils.cleanup(service_name)
        utils.cleanup(app_name)
        os.chdir(cwd)

    def test_mysql_instance_provision(self):
        cwd = os.getcwd()

        dep_id, name = self._provision_mysql_instance()

        show_cmd = ("cld service show --deploy-id {dep_id}").format(dep_id=dep_id)
        self.assertTrue(utils.assert_deploy_complete(show_cmd, "SERVICE_DEPLOYMENT_COMPLETE"),
                        "Service deployment completed")
        utils.cleanup(name)

        os.chdir(cwd)