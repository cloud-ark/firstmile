import os
import subprocess
from common import fm_logger

fmlogging = fm_logger.Logging()

class DockerLib(object):

    def __init__(self):
        self.docker_file_snippets = {}
        self.docker_file_snippets['aws'] = self._aws_df_snippet()
        self.docker_file_snippets['google'] = self._google_df_snippet()

    def _aws_df_snippet(self):
        df = ("FROM lmecld/clis:awscli\n")
        return df

    def _google_df_snippet(self):
        cmd_1 = ("RUN sed -i 's/{pat}access_token{pat}.*/{pat}access_token{pat}/' credentials \n").format(pat="\\\"")

        cmd_2 = ("RUN sed -i \"s/{pat}access_token{pat}.*/{pat}access_token{pat}:{pat}$token{pat},/\" credentials \n").format(pat="\\\"")

        fmlogging.debug("Sed pattern 1:%s" % cmd_1)
        fmlogging.debug("Sed pattern 2:%s" % cmd_2)

        df = ("FROM lmecld/clis:gcloud \n"
              "RUN /google-cloud-sdk/bin/gcloud components install beta \n"
              "COPY . /src \n"
              "COPY google-creds/gcloud  /root/.config/gcloud \n"
              "WORKDIR /root/.config/gcloud \n"
              "{cmd_1}"
              "RUN token=`/google-cloud-sdk/bin/gcloud beta auth application-default print-access-token` \n"
              "{cmd_2}"
              "WORKDIR /src \n"
        )
        df = df.format(cmd_1=cmd_1, cmd_2=cmd_2)

        return df

    def get_dockerfile_snippet(self, key):
        return self.docker_file_snippets[key]

    def _get_cont_id(self, cont_name):
        cont_id_cmd = ("docker ps -a | grep {cont_name} | cut -d ' ' -f 1").format(cont_name=cont_name)

        out = subprocess.Popen(cont_id_cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, shell=True).communicate()[0]
        return out

    def stop_container(self, cont_name, reason_phrase):
        fmlogging.debug("Stopping container %s. Reason: %s" % (cont_name, reason_phrase))
        cont_id = self._get_cont_id(cont_name)
        if cont_id:
            stop_cmd = ("docker stop {cont_id}").format(cont_id=cont_id)
            fmlogging.debug("stop command:%s" % stop_cmd)
            os.system(stop_cmd)

    def remove_container(self, cont_name, reason_phrase):
        fmlogging.debug("Removing container %s. Reason: %s" % (cont_name, reason_phrase))
        cont_id = self._get_cont_id(cont_name)
        if cont_id:
            rm_cmd = ("docker rm -f {cont_id}").format(cont_id=cont_id)
            #rm_cmd = ("docker ps -a | grep {cont_name} | cut -d ' ' -f 1 | xargs docker rm -f").format(cont_name=cont_name)
            fmlogging.debug("rm command:%s" % rm_cmd)
            os.system(rm_cmd)

    def remove_container_image(self, cont_name, reason_phrase):
        fmlogging.debug("Removing container image %s. Reason: %s" % (cont_name, reason_phrase))
        #cont_id = self._get_cont_id(cont_name)
        #if cont_id:
        #rmi_cmd = ("docker rmi -f {cont_id}").format(cont_id=cont_id)
        cont_id_cmd = ("docker images -a | grep {cont_name}  | awk \'{{print $3}}\'").format(cont_name=cont_name)

        cont_id = subprocess.Popen(cont_id_cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, shell=True).communicate()[0]
        if cont_id:
            rmi_cmd =  ("docker rmi -f {cont_id}").format(cont_id=cont_id)
            fmlogging.debug("rmi command:%s" % rmi_cmd)
            os.system(rmi_cmd)

    def build_container_image(self, cont_name, docker_file_name, df_context=''):
        docker_build_cmd = ("docker build -t {cont_name} -f {docker_file_name} {df_context}").format(cont_name=cont_name,
                                                                                                     docker_file_name=docker_file_name,
                                                                                                     df_context=df_context)
        fmlogging.debug("Docker build cmd:%s" % docker_build_cmd)
        os.system(docker_build_cmd)

    def build_ct_image(self, cont_name, docker_file_name, df_context=''):
        build_cmd = ("docker build -t {cont_name} -f {docker_file_name} {df_context}").format(cont_name=cont_name,
                                                                                              docker_file_name=docker_file_name,
                                                                                              df_context=df_context)
        fmlogging.debug("Docker build cmd:%s" % build_cmd)

        try:
            chanl = subprocess.Popen(build_cmd, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, shell=True).communicate()
            err = chanl[1]
            output = chanl[0]
        except Exception as e:
            fmlogging.debug(e)
            raise e
        return err, output

    def run_container(self, cont_name):
        docker_run_cmd = ("docker run -i -t -d {cont_name}").format(cont_name=cont_name)
        fmlogging.debug("Docker run cmd:%s" % docker_run_cmd)
        os.system(docker_run_cmd)

    
    
