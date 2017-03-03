'''
 Copyright (C) Devcentric, Inc - All Rights Reserved
 Unauthorized copying of this file, via any medium is strictly prohibited
 Proprietary and confidential
 Written by Devdatta Kulkarni <devdattakulkarni@gmail.com> December 26 2016
'''

import os
from common import docker_lib

def setup_database(work_dir, db_info, artifact_info):
    "Setup database instance"
    
    if 'setup_file' in db_info:
        db_host = db_info['host']
        db_user = db_info['root_user']
        db_password = db_info['root_password']
        db_setup_file = db_info['setup_file']

        artifact_name = artifact_info['name']
        artifact_version = artifact_info['version']

        cmd = ("mysql -h{db_host} --user={db_user} --password={db_password} < {setup_file}").format(db_host=db_host,
                                                                                                    db_user=db_user,
                                                                                                    db_password=db_password,
                                                                                                    setup_file=db_setup_file)
        cwd = os.getcwd()
        os.chdir(work_dir)

        # Create Dockerfile
        df = ("FROM ubuntu:14.04 \n"
              "RUN apt-get update && apt-get install -y mysql-client-core-5.5\n"
              "COPY {setup_file} . \n"
              "CMD {cmd}"
              ).format(setup_file=db_setup_file, cmd=cmd)

        fp = open("Dockerfile", "w")
        fp.write(df)
        fp.close()
    
        cont_name = ("setup-db-{name}-{version}").format(name=artifact_name,
                                                         version=artifact_version)
        docker_lib.DockerLib().build_container_image(cont_name, "Dockerfile")
        docker_lib.DockerLib().run_container(cont_name)

        os.chdir(cwd)