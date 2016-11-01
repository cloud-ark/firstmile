Local deployment POC
--------------------
Assumptions:
- Docker is installed on the Host
- Python on the Host
- Sample application is an application using MySQL service


Steps:
------
1) Install virtualenv (pip install virtualenv)
2) Create virtualenv (virtualenv test-lme)
3) Start virtualenv (source test-lme/bin/activate)
4) Install lme (pip install -r requirements.txt)
5) Start the server:
   - python app.py
6) Create a deployment
   - cd client; python lmeui.py post
     - this will ask for path of application folder. (Provide the complete app folder path)
     - the deployment action will output a app URL, which can be used to track the deployment
7) Track a deployment
  - python lmeui.py get <url-of-the-deployment> (from step 6)

Deployment related artifacts are stored in: ~/.lme/data/deployments

Sample applications are available in:
https://devdattakulkarni@bitbucket.org/devdattakulkarni/lme-examples.git

Clone the sample repo and provide full path of the sample app that you want to deploy in step 6.

