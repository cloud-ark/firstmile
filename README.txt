Local deployment POC
--------------------
Assumptions:
- Python and Docker are installed on the Host

Sample applications are available in lme-examples repository
(https://devdattakulkarni@bitbucket.org/devdattakulkarni/lme-examples.git)
To test lme you will need to clone lme-examples and use the sample applications provided.


Steps:
------
1) Install virtualenv (pip install virtualenv)
2) Create virtualenv (virtualenv test-lme)
3) Start virtualenv (source test-lme/bin/activate)
4) Install lme (pip install -r requirements.txt)
5) Start the server:
   - python app.py

Deploying through LME UI:
--------------------------
1) Start the UI
   - cd client; python lmeui.py
2) Create a deployment
   - Select the application by navigating to the application folder of the sample application (say, greetings-python)
   - Hit "Deploy"
3) Track the deployment
   - Hit "Track"

Deploying through LME CLI:
---------------------------
1) Install the CLI
   - cd client; python setup.py install
   - This will install the LME cli. You can check the features of the LME cli by using
     lme --help

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
      (virtenv) devdatta@devdatta-ThinkPad-T430:~/Code/lme/client$

2) Deploy the application
   - Navigate to the application folder (say, greetings-python) and then run
      lme deploy --service mysql --cloud local
     This will output application deployment tracking URL

3) Check application status
      lme show --deploy-id <App tracking URL from step 2>


Details:
--------
Deployment related artifacts are stored inside ".lme" folder inside your home directory (~/.lme/data/deployments)
