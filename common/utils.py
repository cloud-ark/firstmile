from common import fm_logger
import os
import shutil
import subprocess
import threading

from common import constants

fmlogging = fm_logger.Logging()

lock = threading.Lock()


def get_id(path, file_name, name, version, s_name, s_version, s_id, cloud,
           cloud_info):
    # Method 1:
    # app_id = ("{app_name}--{app_version}").format(app_name=app_name, app_version=app_version)

    # Method 2:
    # open app_ids.txt file available at APP_STORE_PATH
    lock.acquire()

    try:
        id_count = 1
        if os.path.exists(path + "/" + file_name):
            try:
                f = open(path + "/" + file_name, "r")
                all_lines = f.readlines()
                if all_lines:
                    found_non_deleted_line = False
                    last_index = len(all_lines)-1
                    while not found_non_deleted_line and last_index > -1:
                        last_line = all_lines[last_index]
                        parts = last_line.split(" ")
                        if parts[0] != 'deleted':
                            found_non_deleted_line = True
                        else:
                            last_index = last_index - 1
                    if last_index <= 0 and not found_non_deleted_line:
                        id_count = 1
                    else:
                        last_line_parts = last_line.split(" ")
                        id_count = int(last_line_parts[0]) + 1
                f.close()
            except IOError:
                fmlogging.error("%s does not exist yet. Creating.." % file_name)
    
        f = open(path + "/" + file_name, "a")
        line = str(id_count) + " " + name + "--" + version + " " + cloud
        line = line + " " + s_name + " " + s_version + " " + str(s_id) + "--" + str(cloud_info) + "\n"
        f.write(line)
    finally:
        lock.release()
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

def save_service_instance_ip(file_path, ip):
    app_status_file = open(file_path, "a")
    app_status_file.write("HOST:: " + ip)
    app_status_file.close()

def get_env_vars_string(task_def, service_ip_dict, app_variables,
                        services, prefix, suffix):
    serv = task_def.service_data[0]
    service_name = serv['service']['type']

    for k, v in service_ip_dict.items():
        if k == service_name:
            host = v
            break

    df_env_vars = ''
    if app_variables:
        service_handler = services[service_name]
        service_instance_info = service_handler.get_instance_info()
        service_instance_info['host'] = host
        for key, val in app_variables.iteritems():
            service_var = key[:key.index("_var")]
            env_key = val
            env_val = service_instance_info[service_var]
            generated_val = ("{prefix} {key}{suffix}{value}\n").format(prefix=prefix,
                                                                        suffix=suffix,
                                                                        key=env_key,
                                                                        value=env_val)
            df_env_vars = df_env_vars + generated_val
    return df_env_vars

def parse_artifact_name_and_version(line_contents):
    artifact = line_contents[1].rstrip().lstrip()
    k = artifact.rfind("--")
    artifact_version = artifact[k+2:].rstrip().lstrip()
    artifact_name = artifact[:k]
    return artifact_name, artifact_version

def get_artifact_name_version(id_file_path, id_file_name,
                      status_file_name, artifact_id):
    artifact_name = artifact_version = ''
    if os.path.exists(id_file_path + "/" + id_file_name):
        f = open(id_file_path + "/" + id_file_name)
        all_lines = f.readlines()
        for line in all_lines:
            line_contents = line.split(" ")
            if line_contents[0] == artifact_id:
                artifact_name, artifact_version = parse_artifact_name_and_version(line_contents)

    return artifact_name, artifact_version

def prepare_line(app_line, line_contents, app_version, file_path):
    app_line['dep_id'] = line_contents[0]
    app_line['version'] = app_version
    app_stat_file = open(file_path)
    stat_line = app_stat_file.read()

    parts = stat_line.split(',')
    info = {}
    for p in parts:
        parts_dict = _parse_line(p)
        if parts_dict['name']:
            app_line['name'] = parts_dict['name']
        if parts_dict['cloud']:
            app_line['cloud'] = parts_dict['cloud']
        if parts_dict['status']:
            app_line['status'] = parts_dict['status']
        if parts_dict['url']:
            info['APP URL'] = parts_dict['url']
        if parts_dict['instance_ip']:
            info['HOST IP'] = parts_dict['instance_ip']
        if parts_dict['mysql_instance']:
            info['MySQL instance'] = parts_dict['mysql_instance']
        if parts_dict['mysql_user']:
            info['USER'] = parts_dict['mysql_user']
        if parts_dict['mysql_password']:
            info['PASSWORD'] = parts_dict['mysql_password']
        if parts_dict['mysql_db_name']:
            info['DB_NAME'] = parts_dict['mysql_db_name']
    app_line['info'] = info
    return app_line

def read_statuses_given_id(id_file_path, id_file_name,
                           status_file_name, artifact_id):
    app_lines = list()
    lock.acquire()
    try:
        if os.path.exists(id_file_path + "/" + id_file_name):
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
                        app_line = prepare_line(app_line, line_contents,
                                                artifact_version,
                                                status_file_loc)
                        app_lines.append(app_line)
    finally:
        lock.release()
    return app_lines

def _parse_line(part):
    name = cloud = url = status = ''
    mysql_instance = mysql_user = mysql_password = ''
    mysql_db_name = instance_ip = ''
    units = part.split("::")
    parts_dict = {}
    if part.find("name::") >= 0:
        if len(units) > 2:
            name = units[2]
        else:
            name = units[1]
    elif part.find("cloud::") >= 0:
        # TODO(devkulkarni): Below we are supporting two formats
        # of cloud representation
        # We just want to keep single format.
        if len(units) > 2:
            cloud = units[2]
        else:
            cloud = units[1]
    elif part.find("URL::") >= 0:
        url = units[1]
    elif part.find("HOST::") >= 0:
        instance_ip = units[1]
    elif part.find("status::") >= 0:
        status = units[1]
    elif part.find("INSTANCE::") >= 0:
        mysql_instance = units[1]
    elif part.find("SQL_CONTAINER::") >= 0:
        mysql_instance = units[1]
    elif part.find("USER::") >= 0:
        mysql_user = units[1]
    elif part.find("PASSWORD::") >= 0:
        mysql_password = units[1]
    elif part.find("DB_NAME::") >= 0:
        mysql_db_name = units[1]
    parts_dict['name'] = name
    parts_dict['cloud'] = cloud
    parts_dict['url'] = url
    parts_dict['instance_ip'] = instance_ip
    parts_dict['status'] = status
    parts_dict['mysql_instance'] = mysql_instance
    parts_dict['mysql_user'] = mysql_user
    parts_dict['mysql_password'] = mysql_password
    parts_dict['mysql_db_name'] = mysql_db_name
    return parts_dict

def remove_artifact(dep_id, artifact_id_path, artifact_id_file, artifact_name, artifact_version):
    lock.acquire()

    try:
        os.chdir(constants.APP_STORE_PATH)
    
        id_file_path = artifact_id_path
        id_file_name = artifact_id_file
        f = open(id_file_path + "/" + id_file_name, "r")
        all_lines = f.readlines()
        for idx, line in enumerate(all_lines):
            line_contents = line.split(" ")
            if line_contents[0] == dep_id:
                line_contents_new = []
                line_contents_new.append("deleted")
                line_contents_new.extend(line_contents)
                new_line = " ".join(line_contents_new)
                del all_lines[idx]
                all_lines.insert(idx, new_line)
        f.close()
    
        f = open(id_file_path + "/" + id_file_name, "w")
        f.writelines(all_lines)
        f.flush()
        f.close()
    
        # Remove artifact directory
        os.chdir(artifact_id_path + "/" + artifact_name)
        shutil.rmtree(artifact_version, ignore_errors=True)
    
        os.chdir(constants.APP_STORE_PATH)
    finally:
        lock.release()

def update_service_status(info, status):
    service_name = info['service_name']
    service_version = info['service_version']
    app_status_file = (constants.SERVICE_STORE_PATH + "/{service_name}/{service_version}/service-status.txt").format(service_name=service_name,
                                                                                                                     service_version=service_version)
    fp = open(app_status_file, "a")
    status_line = (", status::{status}").format(status=status)
    fp.write(status_line)
    fp.flush()
    fp.close()

def get_service_info(id_file_path, id_file_name, dep_id):
    info = {}

    lock.acquire()
    try:
        f = open(id_file_path + "/" + id_file_name)
        all_lines = f.readlines()
        for line in all_lines:
            # line structure
            # 1 mysql--2017-02-18-12-29-22 local-docker   --{u'type': u'local-docker'}
            line_contents = line.split(" ")
            if line_contents[0] == dep_id:
                name_version = line_contents[1].rstrip().lstrip()
                k = name_version.rfind("--")
                version = name_version[k+2:].rstrip().lstrip()
    
                fmlogging.debug("Service version:%s" % version)
    
                name = name_version[:k]
                fmlogging.debug("Service name:%s" % name)
    
                cloud = line_contents[2].rstrip().lstrip()
                get_cloud_details = line.split("--")
                cloud_details = get_cloud_details[-1].rstrip().lstrip()
    
                info['dep_id'] = dep_id
                info['app_name'] = ''
                info['service_name'] = name
                info['service_version'] = version
                info['service_id'] = dep_id
                info['cloud'] = cloud
                info['cloud_details'] = cloud_details
    finally:
        lock.release()
    return info

def get_app_and_service_info(id_file_path, id_file_name, dep_id):

    info = {}

    lock.acquire()

    try:
        f = open(id_file_path + "/" + id_file_name)
        all_lines = f.readlines()
        for line in all_lines:
            # line structure
            # 49 greetings-python--2017-01-19-08-54-18 local-docker mysql-greetings-python 2017-01-19-08-54-18
            line_contents = line.split(" ")
            if line_contents[0] == dep_id:
                name_version = line_contents[1].rstrip().lstrip()
                k = name_version.rfind("--")
                app_version = name_version[k+2:].rstrip().lstrip()
    
                fmlogging.debug("App version:%s" % app_version)
    
                name = name_version[:k]
                l = name.rfind("/")
                app_name = name[l+1:].rstrip().lstrip()
                fmlogging.debug("App name:%s" % app_name)
    
                cloud = line_contents[2].rstrip().lstrip()
    
                service_name = ''
                service_version = ''
                service_id = ''
                cloud_details = ''
    
                if len(line_contents) >= 6:
                    service_name = line_contents[3].rstrip().lstrip()
                    service_version = line_contents[4].rstrip().lstrip()
                    service_id = line_contents[5].rstrip().lstrip()
                    # cloud_details are appended as last entry in the line with '--' as the separator
                    prts = service_id.split("--")
                    if prts:
                        service_id = prts[0]
                        cld_details_prts = line.split("--")
                        cloud_details = cld_details_prts[2].rstrip().lstrip()
    
                info['dep_id'] = dep_id
                info['app_name'] = app_name
                info['app_version'] = app_version
                info['service_name'] = service_name
                info['service_version'] = service_version
                info['service_id'] = service_id
                info['cloud'] = cloud
                info['cloud_details'] = cloud_details
    finally:
        lock.release()
    return info

def read_statues(id_file_path, id_file_name, status_file_name, artifact_name,
                 artifact_version):
    app_lines = list()

    lock.acquire()
    try:
        if os.path.exists(id_file_path + "/" + id_file_name):
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
    
                if artifact_name:
                    if found_app_name == artifact_name:
                        app_stat_file = id_file_path + "/" + artifact_name + "/" + app_version + "/" + status_file_name
                    else:
                        app_stat_file = ''
                else:
                    app_stat_file = id_file_path + "/" + found_app_name + "/" + app_version + "/" + status_file_name
                if os.path.exists(app_stat_file):
                    app_line = prepare_line(app_line, line_contents, app_version, app_stat_file)
                    app_lines.append(app_line)
    finally:
        lock.release()
    return app_lines

def read_service_details(id_file_path, id_file_name, details_file_name,
                         artifact_name, artifact_version, artifact_status_lines):

    lock.acquire()
    try:
        if os.path.exists(id_file_path + "/" + id_file_name):
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
                                if 'info' in line and line['version'] == service_version:
                                    artifact_info_dict = line['info']
                                    for serv_detail_line in service_details.split("\n"):
                                        parts = serv_detail_line.split("::")
                                        if len(parts) == 2:
                                            key = parts[0].rstrip().lstrip()
                                            value = parts[1].rstrip().lstrip()
                                            artifact_info_dict[key] = value
                                    line['info'] = artifact_info_dict
    finally:
        lock.release()
    return artifact_status_lines

def delete_tar_file(location, app_name):
    tar_file = location + "/" + app_name + ".tar"
    if os.path.exists(tar_file):
        fmlogging.debug("Deleting app tar file")
        os.remove(tar_file)

def delete_app_folder(location, app_name):
    lib_folder = location + "/" + app_name
    if os.path.exists(lib_folder):
        fmlogging.debug("Deleting app folder")
        shutil.rmtree(lib_folder, ignore_errors=True)

# Google-specific commands
def copy_google_creds(source, dest):
    # Copy google-creds to the app directory
    if not os.path.exists(dest):
        os.mkdir(dest)
    cp_cmd = ("cp -r {google_creds_path} {app_deploy_dir}/.").format(google_creds_path=source,
                                                                     app_deploy_dir=dest)

    fmlogging.debug("Copying google-creds directory..")
    fmlogging.debug(cp_cmd)

    os.system(cp_cmd)

def generate_google_password():
    return generate_password()

def delete_app_lib_folder(location, app_name):
    lib_folder = location + "/" + app_name + "/lib"
    if os.path.exists(lib_folder):
        fmlogging.debug("Deleting lib folder")
        shutil.rmtree(lib_folder, ignore_errors=True)
# Google-specific commands

def delete(info):
    if info['app_name']:
        app_name = info['app_name']
        app_version = info['app_version']
        dep_id = info['dep_id']
        remove_artifact(dep_id, constants.APP_STORE_PATH, "app_ids.txt", app_name, app_version)

    if info['service_name']:
        # Remove service directories as well, if a service has been provisioned
        service_name = info['service_name']
        service_version = info['service_version']
        service_id = info['service_id']

        if service_name:
            remove_artifact(service_id, constants.SERVICE_STORE_PATH,
                            "service_ids.txt", service_name, service_version)

def generate_password():
    import string, random
    all_printable = set(list(string.printable))
    punctuation = set(list(string.punctuation))
    whitespace = set(list(string.whitespace))
    allowed_charset = list(all_printable - punctuation - whitespace)

    #valid_list = []
    #for c in allowed:
    #    if c not in ['/','"','@',' ','\n','\t','\r','\x0b','\x0c', '(', ')', ':', '#', '`', '\'', "'", '\\', '|']:
    #        valid_list.append(c)

    #valid_charset = ''.join(valid_list)

    # Below snippet taken from [1]
    # [1] http://stackoverflow.com/questions/7479442/high-quality-simple-random-password-generator

    length = 8
    random.seed = (os.urandom(1024))
    password = ''.join(random.choice(allowed_charset) for i in range(length))
    
    # first character
    firstchar = random.choice(string.letters)
    password = firstchar + password
    
    # last character
    punct = ['!','$']
    lastchar = random.choice(punct)
    password = password + lastchar
    
    return password

def read_password(path):
    password = ''
    fp = open(path, "r")
    lines = fp.readlines()
    for l in lines:
        if l.find("PASSWORD") >= 0:
            parts = l.split("::")
            password = parts[1].lstrip().rstrip()
            break
    return password

def execute_shell_cmd(cmd):
    fmlogging.debug("Command:%s" % cmd)

    try:
        chanl = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, shell=True).communicate()
        err = chanl[1]
        output = chanl[0]
    except Exception as e:
        fmlogging.debug(e)
        raise e
    return err, output

## AWS-specific methods
def read_environment_name(app_dir):
#    cwd = os.getcwd()
#    os.chdir(app_dir)
    fp = open(app_dir + "/env-name", "r")
    env_name = fp.readline()
    env_name = env_name.rstrip().lstrip()
#    os.chdir(cwd)
    return env_name

def get_aws_region():
    aws_creds_path = constants.APP_STORE_PATH + "/aws-creds"
    fp = open(aws_creds_path + "/config", "r")
    lines = fp.readlines()
    for line in lines:
        line = line.rstrip()
        if line.find("region") >= 0:
            parts = line.split("=")
            region = parts[1].rstrip().lstrip()
            return region

def generate_aws_password():
    #  Can be any printable ASCII character except "/", """, or "@"
    return generate_password()

def check_if_available(line):
    instance_available = ''
    if line.find("DBInstanceStatus") >= 0:
        parts = line.split(":")
        status = parts[1].rstrip().lstrip().replace("\"", "").replace(",", "")
        if status == 'available':
            instance_available = True
    return instance_available
## AWS-specific methods
