'''
 Copyright (C) Devcentric, Inc - All Rights Reserved
 Unauthorized copying of this file, via any medium is strictly prohibited
 Proprietary and confidential
 Written by Devdatta Kulkarni <devdattakulkarni@gmail.com> December 23, 2016
'''

import logging
import prettytable
import os

from cliff.command import Command

import common
import deployment as dp

class ServiceShow(Command):
    "Display service instance information"

    log = logging.getLogger(__name__)

    def _service_name_show(self, service_name):
        result = dp.Deployment().get_service_info(service_name)
        x = prettytable.PrettyTable()
        x.field_names = ["Deploy ID", "Service Version", "Cloud",
                         "Status", "Service Info"]

        if result:
            pretty_table = common.artifact_name_show(result, x)

        self.app.stdout.write("%s\n" % pretty_table)

    def _deploy_id_show(self, deploy_id):
        result = dp.Deployment().get_service_info_from_id(deploy_id)
        x = prettytable.PrettyTable()
        x.field_names = ["Deploy ID", "Service Version", "Cloud",
                         "Status", "Service Info"]

        if result:
            pretty_table = common.artifact_name_show(result, x)

        self.app.stdout.write("%s\n" % pretty_table)

    def get_parser(self, prog_name):
        parser = super(ServiceShow, self).get_parser(prog_name)

        parser.add_argument('--service-name',
                                 dest='service_name',
                                 help="Name of the service")

        parser.add_argument('--deploy-id',
                                 dest='deploy_id',
                                 help="Deployment id")

        return parser

    def take_action(self, parsed_args):
        service_name = parsed_args.service_name
        dep_id = parsed_args.deploy_id
        if not service_name and not dep_id:
            dep_id = raw_input("Please enter service deploy id>")

        if service_name:
            self._service_name_show(service_name)

        if dep_id:
            self._deploy_id_show(dep_id)


class ServiceDeploy(Command):
    "Provision a service instance"

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(ServiceDeploy, self).get_parser(prog_name)

        parser.add_argument('--service',
                                 dest='service_name',
                                 help="Name of the required service (E.g.: mysql)")

        parser.add_argument('--cloud',
                            dest='cloud',
                            help="Destination to deploy application (local-docker, aws, google)")

        return parser
    
    def _read_service_setup_script(self, service_info):
        for serv in service_info:
            if 'setup_script' in serv['service']:
                setup_script_path = serv['service']['setup_script']
                if not os.path.exists(setup_script_path):
                    logging.error("Setup script path %s does not exist." % setup_script_path)
                    #sys.exit(0)
                setup_script_fp = open(setup_script_path, "r")
                setup_script_content = setup_script_fp.read()
                serv['service']['setup_script_content'] = setup_script_content

    def take_action(self, parsed_args):
        #self.log.info('Deploying service')

        service = parsed_args.service_name
        dest = parsed_args.cloud

        common.verify_inputs(service, dest)

        service_info = common.read_service_info()
        if not service_info:
            service_details = {}
            service_list = []
            service_details['type'] = 'mysql'
            service_info = {}
            service_info['service'] = service_details
            service_list.append(service_info)
            service_info = service_list

        self._read_service_setup_script(service_info)

        cloud_info = common.read_cloud_info()
        
        if not cloud_info:
            cloud_info = {}
            dest = parsed_args.cloud
            if dest:
                if dest.lower() == common.LOCAL_DOCKER:
                    cloud_info['type'] = common.LOCAL_DOCKER
                if dest.lower() == common.AWS:
                    common.setup_aws()
                    cloud_info['type'] = common.AWS
                if dest.lower() == common.GOOGLE:
                    common.setup_google()
                    project_location = os.getcwd()
                    project_id = ''
                    user_email = ''
                    project_id, user_email = common.get_google_project_user_details(project_location)
                    print("Using project_id:%s" % project_id)
                    print("Using user email:%s" % user_email)
                    cloud_info['type'] = common.GOOGLE
                    cloud_info['project_id'] = project_id
                    cloud_info['user_email'] = user_email
        else:
            if dest and cloud_info['type'] != dest:
                print("Looks like there is cld.yaml present in the directory and the value of the cloud flag differs between command line and cld.yaml.")
                print("Using values in cld.yaml.")

        self.dep_track_url = dp.Deployment().create_service_instance(service_info, cloud_info)
        self.log.debug("Service deployment tracking url:%s" % self.dep_track_url)

        l = self.dep_track_url.rfind("/")
        dep_id = self.dep_track_url[l+1:]

        x = prettytable.PrettyTable()
        x.field_names = ["Service Name", "Deploy ID", "Cloud"]

        cloud = cloud_info['type']
        for serv in service_info:
            service_name = serv['service']['type']
            x.add_row([service_name, dep_id, cloud])
            self.app.stdout.write("%s\n" % x)
            self.log.debug(x)