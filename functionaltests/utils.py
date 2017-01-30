'''
Created on Jan 27, 2017

@author: devdatta
'''

import os
import subprocess
import time
import yaml

MAX_WAIT_COUNT = 180
SAMPLE_REPO = "https://devdattakulkarni@bitbucket.org/devdattakulkarni/lme-examples.git"
SAMPLE_REPO_NAME = "lme-examples"


def parse_service_info(lines):
    host = ''
    db_name = ''
    user = ''
    password = ''
    for line in lines.split("\n"):
        parts = line.split("|")
        parts = [item.rstrip() for item in parts]
        parts = [item.lstrip() for item in parts]

        if len(parts) >= 4:
            if parts[5].find("HOST IP") >= 0:
                prts = parts[5].split(":")
                host = prts[1].rstrip().lstrip()
            if parts[5].find("DB_NAME") >= 0:
                prts = parts[5].split(":")
                db_name = prts[1].rstrip().lstrip()
            if parts[5].find("USER") >= 0:
                prts = parts[5].split(":")
                user = prts[1].rstrip().lstrip()
            if parts[5].find("PASSWORD") >= 0:
                prts = parts[5].split(":")
                password = prts[1].rstrip().lstrip()
    return host, db_name, user, password

def contains(target, lines):
    found = False
    for line in lines.split("\n"):
        if line.find(target) >= 0:
            found = True
            break
    return found

def create_cld_yaml_file(target_dir, data):
    cwd = os.getcwd()
    os.chdir(target_dir)

    with open('cld.yaml', 'w') as outfile:
        yaml.dump(data, outfile, default_flow_style=False)

    os.chdir(cwd)

def parse_app_url(lines):
    for line in lines.split("\n"):
        parts = line.split("|")
        parts = [item.rstrip() for item in parts]
        parts = [item.lstrip() for item in parts]
        if len(parts) >= 6:
            if parts[5].find("APP URL") >= 0:
                parts[5] = parts[5].rstrip().lstrip()
                prts = parts[5].split(" ")
                app_url = prts[3]
                return app_url

def parse_dep_id(cloud, lines):
    #print("Lines:%s" % lines)
    for line in lines.split("\n"):
        #print("Line:%s" % line)
        parts = line.split("|")
        parts = [item.rstrip() for item in parts]
        parts = [item.lstrip() for item in parts]
        if parts and cloud in parts:
            name = parts[1].rstrip().lstrip()
            dep_id = parts[2].rstrip().lstrip()
            print("Dep id:%s Name:%s" % (dep_id, name))
            return dep_id, name


def assert_deploy_complete(show_cmd, status, wait_count=MAX_WAIT_COUNT):
    count = 0
    while count < wait_count:
        try:
            output = subprocess.Popen(show_cmd,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE,
                                      shell=True).communicate()[0]
            #print("Show output:%s" % output)
        except Exception as e:
            print(e)

        for line in output.split("\n"):
            parts = line.split(" ")
            if status in parts:
                return True

        count = count + 1
        time.sleep(1)
    return False


def cleanup(name):
    cmd = ("docker ps | grep {name} | head -1 | awk '{{print $1}}' | xargs docker stop").format(name=name)
    os.system(cmd)
    
    cmd = ("docker images | grep {name} | head -1 | awk '{{print $3}}' | xargs docker rmi -f").format(name=name)
    os.system(cmd)
    
    cmd = ("docker ps -a | grep {name} | head -1 | awk '{{print $1}}' | xargs docker rm").format(name=name)
    os.system(cmd)
