FirstMile CLI 
------------------
FirstMile supports building and deploying Python Flask web applications to target clouds (Google and Amazon)
without requiring you to make any changes to application code.
You can also test applications locally by deploying them in FirstMile's Docker-based sandbox.
FirstMile also supports provisioning service instances (such as MySQL, Google Cloud SQL, Amazon RDS).


Installation
--------------
Run ./install.sh


Deployment to local Docker sandbox:
----------------------------------------
1) Deploy hello-world sample application:
   - Navigate to the application folder (cd ../firstmile-samples/hello-world)
   - Deploy application:
     > cld app deploy --cloud local-docker
     
     +------------------+-----------+-----------------+
     |     App Name     | Deploy ID |    Cloud        |
     +------------------+-----------+-----------------+
     | hello-world      |    1      | local-docker    |
     +------------------+-----------+-----------------+

2) Check deployment status
   > cld app show --deploy-id 1
   
   +------------------+-----------+---------------------+--------------+---------------------------------------+
   |     App Name     | Deploy ID |        Status       | Cloud        |                App URL                |
   +------------------+-----------+---------------------+--------------+---------------------------------------+
   | hello-world      |    1      | DEPLOYMENT_COMPLETE | local-docker | http://172.0.0.1                      |
   +------------------+-----------+---------------------+--------------+---------------------------------------+


Deployment to Amazon Elastic Beanstalk:
----------------------------------------
1) Sign up for Amazon AWS account
2) Login to Amazon AWS web console and from the IAM panel do following:
   - Create a IAM User (choose any name)
   - Grant following permission to the user: "AWSElasticBeanstalkFullAccess - AWS Managed Policy" by
     clicking the "Add permissions" button on the user panel.
3) Note down SECRET_ACCESS_KEY and ACCESS_KEY_ID for this user. Provide these values when asked by cld.

4) Deploy hello-world sample application:
   - Navigate to the application folder (cd ../firstmile-samples/hello-world)
   - Deploy application:
     > cld app deploy --cloud aws
     
     +------------------+-----------+------------+
     |     App Name     | Deploy ID |    Cloud   |
     +------------------+-----------+------------+
     | hello-world      |    2      |     aws    |
     +------------------+-----------+------------+

5) Check deployment status
   > cld app show --deploy-id 2
   
   +------------------+-----------+---------------------+--------------+---------------------------------------+
   |     App Name     | Deploy ID |        Status       |     Cloud    |                App URL                |
   +------------------+-----------+---------------------+--------------+---------------------------------------+
   | hello-world      |    2      | DEPLOYMENT_COMPLETE |      aws     | <App URL on AWS>                      |
   +------------------+-----------+---------------------+--------------+---------------------------------------+


Deployment to Google App Engine:
--------------------------------
1) Sign up for a Google cloud account by visiting https://console.cloud.google.com
2) In order to deploy an application on Google App Engine, you will need to first
   create a Google App Engine project from the GAE Console.
   - Create a project and note down the Project ID (Note that it is important to use Project ID and not the Project name).
3) Deploy sample application greetings-python:
   - Navigate to the application folder (cd ../firstmile-samples/greetings-python)
   - Deploy application: 
     > cld app deploy --cloud google --service mysql

     +------------------+-----------+--------+
     |     App Name     | Deploy ID | Cloud  |
     +------------------+-----------+--------+
     | greetings-python |    3      | google |
     +------------------+-----------+--------+

4) Check deployment status
   > cld app show --deploy-id 1

   +------------------+-----------+---------------------+--------+---------------------------------------+
   |     App Name     | Deploy ID |        Status       | Cloud  |                App URL                |
   +------------------+-----------+---------------------+--------+---------------------------------------+
   | greetings-python |    3      | DEPLOYMENT_COMPLETE | google |  https://greetings-python.appspot.com |
   +------------------+-----------+---------------------+--------+---------------------------------------+

Note:
- Your application and all its resources will be deployed in the us-central region of GAE


App commands:
--------------
1) cld app deploy --cloud <cloud>
2) cld app deploy --cloud <cloud> --service mysql
3) cld app show --deploy-id <deploy-id>
4) cld app show --app-name <app-name>
   E.g.:
   cld app show --app-name express-checkout
+-----------+---------------------+--------+-----------------------------------------------------------------------------+
| Deploy ID |     App Version     | Cloud  |                                   App URL                                   |
+-----------+---------------------+--------+-----------------------------------------------------------------------------+
|    153    | 2016-12-19-14-47-41 | google |                  https://express-checkout-153019.appspot.com                |
|    154    | 2016-12-19-14-59-34 |  aws   |  http://express-checkout-2016-12-19-14-59-34.us-west-2.elasticbeanstalk.com |
|    155    | 2016-12-19-15-14-52 | local  |                            http://172.17.1.10:5000                          |
+-----------+---------------------+--------+-----------------------------------------------------------------------------+

5) cld app show --cloud <cloud>
   E.g.:
   cld app show --cloud google

+-----------+------------------+---------------------+----------------------------------------------+
| Deploy ID |     App Name     |     App Version     |                   App URL                    |
+-----------+------------------+---------------------+----------------------------------------------+
|    104    |   hello-world    | 2016-12-18-11-22-40 |    https://hello-world-152322.appspot.com    |
|    145    | greetings-python | 2016-12-19-11-52-40 |     https://greetings-python.appspot.com     |
|    151    | express-checkout | 2016-12-19-13-40-03 |  https://express-checkout-153019.appspot.com |
+-----------+------------------+---------------------+----------------------------------------------+

6) cld app logs --deploy-id <deploy-id>
7) cld app delete --deploy-id <deploy-id>


Service commands:
------------------
1) cld service provision --service <service-name>
2) cld service show --service-name <service-name>
3) cld service list
4) cld service delete --deploy-id <deploy-id>
5) cld service restrict-access --deploy-id <deploy-id>



Deploying using YAML file
--------------------------
FirstMile supports YAML file for deployments.

The yaml file needs to be named 'cld.yaml' and it needs to be placed in the application directory.

cld.yaml allows providing of all the inputs to FirstMile CLI
in one step instead of using different command line flags.


Structure of YAML file:
-----------------------
The YAML file consists of three sections: application, services, cloud.
The cloud section is compulsory whereas application and services section
can be included depending on whether you want to deploy a service instance
or an application. Below is an example of YAML file containing all three sections.

+++++++++++++++++++++++++++++++++++++++
application:
  type: python
  entry_point: application.py
  env_variables:
    MY_VAR1: VALUE1
    MY_VAR2: VALUE2
services:
  - service:
      type: mysql
cloud:
  type: google
  project_id: greetings-python
  user_email: cc1h499@gmail.com
+++++++++++++++++++++++++++++++++++++++

Here are some examples of YAML file for different deployments.

1) Deploying MySQL service instance locally
--
services:
  - service:
      type: mysql
cloud:
  type: local-docker
--

2) Deploying Cloud SQL service instance on Google cloud
--
services:
  - service:
      type: mysql
cloud:
  type: google
  project_id: greetings-python
  user_email: cc1h499@gmail.com
--

3) Deploying RDS instance on AWS cloud
--
services:
  - service:
      type: mysql
cloud:
  type: aws
  SECRET_ACCESS_KEY: secret-access-key
  ACCESS_KEY_ID: access-key-id
--

4) Deploying application on Google cloud and using env_variables to 
   connect to an existing Cloud SQL instance:
--
application:
  type: python
  entry_point: application.py
  env_variables:
    DB: testdb
    HOST: 107.178.214.1
    USER: testuser
    PASSWORD: testpass123!@#
cloud:
  type: google
  project_id: greetings-python
  user_email: cc1h499@gmail.com
--

