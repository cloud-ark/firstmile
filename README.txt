LME - Local Multi-cloud Engine
-------------------------------
LME supports building and deploying Python web applications to target clouds (Google and Amazon)
without requiring you to make any changes to application code.
Applications are deployed to Google App Engine and Amazon Elastic Beanstalk.
You can also deploy application locally (on your machine) for local testing.

Pre-requisites:
---------------
You will need Python (2.7 or above) and Docker installed on your machine to use LME.

Sample applications:
--------------------
Following sample applications are available in lme-examples repository
(https://devdattakulkarni@bitbucket.org/devdattakulkarni/lme-examples.git)
- hello-world
- greetings-python
- express-checkout

greetings-python and express-checkout applications depend on a MySQL database for their correct functioning.

To test lme you can clone lme-examples and use these sample applications.

Setting up LME:
---------------
Follow these steps to setup and run LME server and install LME CLI on your machine.

1) Install virtualenv (pip install virtualenv)
2) Create virtualenv (virtualenv test-lme)
3) Start virtualenv (source test-lme/bin/activate)
4) Install lme
   - git clone https://devdattakulkarni@bitbucket.org/devdattakulkarni/lme.git
   - cd lme
   - pip install -r requirements.txt
5) Start the LME server:
   - python app.py
6) Install the LME CLI
   - Open a new terminal window and navigate to the directory where you cloned
     the lme repository. Go inside the "client" folder inside this directory
     and install the client.
   - cd client; sudo python setup.py install
     - This will install the LME cli.
     - You can check the features of the LME cli by using "lme --help"

      (virtenv) devdatta@devdatta-ThinkPad-T430:~/Code/lme/client$ lme deploy --help
      usage: lme deploy [-h] [--service SERVICE] [--cloud CLOUD]

      Build and deploy application

      optional arguments:
      -h, --help         show this help message and exit
      --service SERVICE  Name of the required service (e.g.: MySQL)
      --cloud CLOUD      Destination to deploy application (local, AWS, Google)

       (virtenv) devdatta@devdatta-ThinkPad-T430:~/Code/lme/client$ lme show --help
       usage: lme show [-h] [--deploy-id DEPLOYID]

       Show application status

       optional arguments:
       -h, --help            show this help message and exit
       --deploy-id DEPLOYID  Deployment ID/URL

Deploying applications:
-----------------------
1) Navigate to the application folder (say, greetings-python) and then run
      lme deploy --service mysql --cloud local
   This will show output of following nature.

+------------------+-----------+--------+
|     App Name     | Deploy ID | Cloud  |
+------------------+-----------+--------+
| greetings-python |    1      | local  |
+------------------+-----------+--------+

2) Use the deploy-id to check the deployment status
      lme show --deploy-id 1

+------------------+-----------+---------------------+--------+--------------------------------------------+
|     App Name     | Deploy ID |        Status       | Cloud  |                App URL                     |
+------------------+-----------+---------------------+--------+--------------------------------------------+
| greetings-python |    1      | DEPLOYMENT_COMPLETE | local  |  http://172.17.1.09:5000                   |
+------------------+-----------+---------------------+--------+--------------------------------------------+

3) You don't have to specify the "service" flag if an application does not need MySQL database for its functioning.
   The hello-world application is of this nature. You can deploy it simply by executing
   lme deploy --cloud <local|google|aws> command

Deployment to Google App Engine:
--------------------------------
1) Sign up for a Google cloud account by visiting https://console.cloud.google.com
2) In order to deploy an application on Google App Engine, you will need to first
   create a Google App Engine project from the GAE Console.
   - Create a project and note down the Project ID.
3) Deploy the application by navigating to the application folder and executing following command:
   lme deploy --cloud google --service mysql

+------------------+-----------+--------+
|     App Name     | Deploy ID | Cloud  |
+------------------+-----------+--------+
| greetings-python |    2      | google |
+------------------+-----------+--------+

4) Check deployment status

lme show --deploy-id 2
+------------------+-----------+---------------------+--------+---------------------------------------+
|     App Name     | Deploy ID |        Status       | Cloud  |                App URL                |
+------------------+-----------+---------------------+--------+---------------------------------------+
| greetings-python |    2      | DEPLOYMENT_COMPLETE | google |  https://greetings-python.appspot.com |
+------------------+-----------+---------------------+--------+---------------------------------------+

Note:
- Your application and all its resources will be deployed in the us-central region of GAE


Deployment to Amazon Elastic Beanstalk:
----------------------------------------
1) Sign up for Amazon AWS account
2) Login to Amazon AWS web console and from the IAM panel do following:
   - Create a IAM User (choose any name)
   - Grant following permission to the user: "AWSElasticBeanstalkFullAccess - AWS Managed Policy" by
     clicking the "Add permissions" button on the user panel.
3) Note down SECRET_ACCESS_KEY and ACCESS_KEY_ID for this user. Provide these values when asked by LME.

4) Deploy the application by navigating to the application folder:
   lme deploy --cloud aws --service mysql

5) Check deployment status
   lme show --deploy-id <deploy-id>

Note:
- Your application and all its resources will be deployed in the us-west-2 region of Amazon ElasticBeanstalk


All available commands:
------------------------
1) lme deploy --cloud <cloud>
2) lme deploy --cloud <cloud> --service mysql
3) lme show --deploy-id <deploy-id>
4) lme show --app-name <app-name>
   E.g.:
   lme show --app-name express-checkout
+-----------+---------------------+--------+-----------------------------------------------------------------------------+
| Deploy ID |     App Version     | Cloud  |                                   App URL                                   |
+-----------+---------------------+--------+-----------------------------------------------------------------------------+
|    153    | 2016-12-19-14-47-41 | google |                  https://express-checkout-153019.appspot.com                |
|    154    | 2016-12-19-14-59-34 |  aws   |  http://express-checkout-2016-12-19-14-59-34.us-west-2.elasticbeanstalk.com |
|    155    | 2016-12-19-15-14-52 | local  |                            http://172.17.1.10:5000                          |
+-----------+---------------------+--------+-----------------------------------------------------------------------------+

5) lme show --cloud <cloud>
   E.g.:
   lme show --cloud google

+-----------+------------------+---------------------+----------------------------------------------+
| Deploy ID |     App Name     |     App Version     |                   App URL                    |
+-----------+------------------+---------------------+----------------------------------------------+
|    104    |   hello-world    | 2016-12-18-11-22-40 |    https://hello-world-152322.appspot.com    |
|    145    | greetings-python | 2016-12-19-11-52-40 |     https://greetings-python.appspot.com     |
|    151    | express-checkout | 2016-12-19-13-40-03 |  https://express-checkout-153019.appspot.com |
+-----------+------------------+---------------------+----------------------------------------------+


Deploying through LME UI (Under development):
---------------------------------------------
1) Start the UI
   - cd client; python lmeui.py
2) Create a deployment
   - Select the application by navigating to the application folder of the sample application (say, greetings-python)
   - Hit "Deploy"
3) Track the deployment
   - Hit "Track"


Details:
--------
- Deployment related artifacts are stored inside ".lme" folder inside your home directory (~/.lme/data/deployments)