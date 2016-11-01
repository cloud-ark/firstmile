Install virtualenv; start virtualenv

pip install -r requirements.txtx


Start the server:
- python app.py

Send requests:
- cd client;

- Create a deployment
  - python lmeui.py 'post' (this will initiate a deployment of express-checkout application to local cloud)

- Track a deployment
  - python lmeui.py 'get' <url-of-the-deployment>


App data is stored in: ~/.lme/data/deployments/<app-name>

