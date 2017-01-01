'''
Created on Dec 23, 2016

@author: devdatta
'''
import os
import logging

def get_id(path, file_name, name, version, cloud):
    # Method 1:
    # app_id = ("{app_name}--{app_version}").format(app_name=app_name, app_version=app_version)

    # Method 2:
    # open app_ids.txt file available at APP_STORE_PATH
    id_count = 1
    if os.path.exists(path + "/" + file_name):
        try:
            f = open(path + "/" + file_name, "r")
            all_lines = f.readlines()
            if all_lines:
                last_line = all_lines[-1]
                last_line_parts = last_line.split(" ")
                id_count = int(last_line_parts[0]) + 1
            f.close()
        except IOError:
            logging.error("app_ids.txt does not exist yet. Creating..")

    f = open(path + "/" + file_name, "a")
    f.write(str(id_count) + " " + name + "--" + version + " " + cloud + "\n")
    return id_count

def update_status(file_path, status):
    app_status_file = open(file_path, "a")
    status = "status::" + status
    app_status_file.write(status + ", ")
    app_status_file.close()

def update_ip(file_path, ip):
    app_status_file = open(file_path, "a")
    if ip.find("http") < 0:
        ip = "http://" + ip
    app_status_file.write("URL:: " + ip)
    app_status_file.close()

def get_artifact_name_version(id_file_path, id_file_name,
                      status_file_name, artifact_id):
    f = open(id_file_path + "/" + id_file_name)
    all_lines = f.readlines()
    for line in all_lines:
        line_contents = line.split(" ")
        if line_contents[0] == artifact_id:
            artifact = line_contents[1].rstrip().lstrip()
            k = artifact.rfind("--")
            artifact_version = artifact[k+2:].rstrip().lstrip()
            artifact_name = artifact[:k]
            return artifact_name, artifact_version

def read_statuses_given_id(id_file_path, id_file_name,
                           status_file_name, artifact_id):
    app_lines = list()
    f = open(id_file_path + "/" + id_file_name)
    all_lines = f.readlines()
    for line in all_lines:
        line_contents = line.split(" ")

        app_line = {}

        if line_contents[0] == artifact_id:
            artifact = line_contents[1].rstrip().lstrip()
            k = artifact.rfind("--")
            artifact_version = artifact[k+2:].rstrip().lstrip()
            artifact_name = artifact[:k]

            status_file_loc = id_file_path + "/" + artifact_name + "/"
            status_file_loc = status_file_loc + artifact_version + "/" + status_file_name

            if os.path.exists(status_file_loc):
                app_line['dep_id'] = line_contents[0]
                app_line['version'] = artifact_version
                app_stat_file = open(status_file_loc)
                stat_line = app_stat_file.read()

                parts = stat_line.split(',')
                cloud = ''
                url = ''
                for p in parts:
                    if p.find("cloud::") >= 0:
                        cld = p.split("::")
                        if len(cld) > 2:
                            cloud = cld[2]
                        else:
                            cloud = cld[1]
                    if p.find("URL::") >= 0:
                        u = p.split("::")
                        url = u[1]
                app_line['cloud'] = cloud
                app_line['info'] = {'url': url}

                app_lines.append(app_line)

    return app_lines

def read_statues(id_file_path, id_file_name, status_file_name, artifact_name,
                 artifact_version):
    app_lines = list()

    f = open(id_file_path + "/" + id_file_name)
    all_lines = f.readlines()
    for line in all_lines:
        line_contents = line.split(" ")
        app_line = {}

        app_version = line_contents[1]
        k = app_version.find("--")
        found_app_name = app_version[:k]

        if not artifact_version:
            app_version = app_version[k+2:].rstrip().lstrip()
        else:
            app_version = artifact_version

        if found_app_name == artifact_name:

            app_stat_file = id_file_path + "/" + artifact_name + "/" + app_version + "/" + status_file_name

            if os.path.exists(app_stat_file):
                app_line['dep_id'] = line_contents[0]
                app_line['version'] = app_version
                app_stat_file = open(app_stat_file)
                stat_line = app_stat_file.read()

                parts = stat_line.split(',')
                cloud = ''
                url = ''
                for p in parts:
                    if p.find("cloud::") >= 0:
                        cld = p.split("::")
                        if len(cld) > 2:
                            cloud = cld[2]
                        else:
                            cloud = cld[1]
                    if p.find("URL::") >= 0:
                        u = p.split("::")
                        url = u[1]
                app_line['cloud'] = cloud
                app_line['info'] = {'url': url}

                app_lines.append(app_line)
    return app_lines

def read_service_details(id_file_path, id_file_name, details_file_name,
                         artifact_name, artifact_version, artifact_status_lines):

    f = open(id_file_path + "/" + id_file_name)
    all_lines = f.readlines()

    service_details = ''
    for line in all_lines:
        line_contents = line.split(" ")
        app_line = {}

        service_version = line_contents[1]
        k = service_version.find("--")
        found_app_name = service_version[:k]
        if not artifact_version:
            service_version = service_version[k+2:].rstrip().lstrip()
        else:
            service_version = artifact_version

        if found_app_name == artifact_name:
            service_details_file = id_file_path + "/" + artifact_name + "/" + service_version + "/" + details_file_name

            if os.path.exists(service_details_file):
                fp = open(service_details_file)
                service_details = fp.read()

                if service_details:
                    artifact_info_dict = ''
                    for line in artifact_status_lines:
                        if line['info'] and line['version'] == service_version:
                            artifact_info_dict = line['info']
                            for serv_detail_line in service_details.split("\n"):
                                parts = serv_detail_line.split("::")
                                if len(parts) == 2:
                                    key = parts[0].rstrip().lstrip()
                                    value = parts[1].rstrip().lstrip()
                                    artifact_info_dict[key] = value
                            line['info'] = artifact_info_dict

    return artifact_status_lines

def copy_google_creds(source, dest):
    # Copy google-creds to the app directory
    if not os.path.exists(dest):
        os.mkdir(dest)
    cp_cmd = ("cp -r {google_creds_path} {app_deploy_dir}/.").format(google_creds_path=source,
                                                                     app_deploy_dir=dest)

    logging.debug("Copying google-creds directory..")
    logging.debug(cp_cmd)

    os.system(cp_cmd)