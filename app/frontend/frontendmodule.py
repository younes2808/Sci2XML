import subprocess
import requests
import re
import getpass
from flask import Flask, jsonify, make_response, request
from pyngrok import ngrok, conf
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    force=True,
    handlers=[
        logging.FileHandler("app.log"),  # Log to a file named 'app.log'
        logging.StreamHandler(sys.stdout)  # Also log to console
    ]
)

def start_localtunnel(port):
  """
  Starts a localtunnel instance and returns the public URL and password.

  Paramaters:
  port: port number to host on.

  Returns:
  tuple: A tuple containing the public URL and password.
  """
  logging.info(f"[frontendmodule.py] Starting Localtunnel.")

  # Get password (which is also the public facing ip adress): 
  res = requests.get('https://ipv4.icanhazip.com')
  passw = res.content.decode('utf8')
  logging.info(f"[frontendmodule.py] Password is: {passw}.")

  # Running localtunnel command:
  URL = subprocess.Popen(["npx", "localtunnel", "--port", port], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
  logging.info(f"[frontendmodule.py] URL is: {URL}, {URL.stdout.readline}.")
  for line in iter(URL.stdout.readline, ''):
    match = re.search(r"(https://[a-zA-Z0-9-]+\.loca\.lt)", line)
    if match:
        public_url = match.group(1)
        logging.info(f"[frontendmodule.py] URL Found: {public_url}")
        break
    else:
      logging.error(f"[frontendmodule.py] Could not find URL.")
      public_url = "URL NOT FOUND"
      break

  return public_url, passw

def start_ngrok(port):
  """
  Starts a ngrok instance and returns the public URL and password.

  Paramaters:
  port: port number ngrok should be hosted on.

  Returns:
  tuple: A tuple containing the public URL and password.
  """
  logging.info(f"[frontendmodule.py] Starting Ngrok.")

  envdict = get_envdict()
  if ("authtoken" not in envdict): # If key doesnt exist, create it with default value 'None':
      with open("/content/.env", "a") as f:
          f.write("authtoken=None\n")
      # File is automatically closed after exiting the 'with' block
  envdict = get_envdict()
  if (envdict["authtoken"] != "None"): # Check to see if authtoken is set
    conf.get_default().auth_token = envdict["authtoken"]
  else:
    # Lets user write their auth token:
    print("Enter your Ngrok Authtoken. Token can be found here: https://dashboard.ngrok.com/get-started/your-authtoken")
    print("Please note: You may need to enter the token and press Enter twice before Ngrok responds.")
    conf.get_default().auth_token = getpass.getpass()

  # Open a ngrok tunnel to the localhost:
  try:
      public_url = ngrok.connect(port).public_url
      print(f" * ngrok tunnel \"{public_url}\" -> \"http://127.0.0.1:{port}\"")
      logging.info(f"[frontendmodule.py] Successfully opened ngrok tunnel.")
  except Exception as e:
      logging.error(f"[frontendmodule.py] An error occurred while trying to open ngrok tunnel: {e}", exc_info=True)
  
  return public_url, "no password needed"

def start_streamlit(tunnel, portnr):
  """
  Starts a Streamlit application. Then calls on function to start localtunnel.

  Paramaters:
  tunnel: which tunnel provider. Either Localtunnel or Ngrok
  portnr: port number

  Returns:
  None
  """
  logging.info(f"[frontendmodule.py] Starting Streamlit.")
  # Launching streamlit on localhost:
  logfile = open("logs.txt", "w")
  URL = subprocess.Popen(["streamlit", "run", "app/frontend/app.py", "&"], stdout=logfile, stderr=logfile, text=True, cwd="/content/Sci2XML")

  # Exposing localhost through tunnel, depending on which tunnel is selected at launch:
  if (tunnel == "localtunnel"):
    ## Launch Localtunnel ##
    url, passw = start_localtunnel("8501")
  elif (tunnel == "ngrok"):
    ## Launch Ngrok ##
    url, passw = start_ngrok("8501")
  
  # Save url and password to file, in case it doesnt print to console.
  with open("urlpasslog.txt", "w") as file:
    file.write(url)
    file.write("\n")
    file.write(passw)
  # File is automatically closed after exiting the 'with' block
    
  return url, passw

def start_API(tunnel, portnr):
  """
  Starts only the API. Then calls on function to start localtunnel.

  Paramaters:
  tunnel: which tunnel provider. Either Localtunnel or Ngrok
  portnr: port number

  Returns:
  None
  """
  logging.info(f"[frontendmodule.py] Exposing API.")

  # Exposing localhost through tunnel, depending on which tunnel is selected at launch:
  if (tunnel == "localtunnel"):
    ## Localtunnel ##
    url, passw = start_localtunnel(portnr)
  elif (tunnel == "ngrok"):
    ## Ngrok ##
    url, passw = start_ngrok(portnr)

  # Save url and password to file, in case it doesnt print to console.
  with open("urlpasslog.txt", "w") as file:
    file.write(url)
    file.write("\n")
    file.write(passw)
  # File is automatically closed after exiting the 'with' block
    
  return url, passw

def get_envdict():
    """
    Gets the content of the .env file and creates a dictionary of its elements.

    Parameters:
    None

    Returns:
    envdict (dict): A dictionary with the contents of the .env file.
    """
    # Open and read .env file:
    try:
        with open("/content/.env", "r") as f:
            env = f.read()
        # File is automatically closed after exiting the 'with' block
        logging.info(f"[frontendmodule.py] Successfully opened .env file.")
    except Exception as e:
        logging.error(f"[frontendmodule.py] An error occurred while opening .env file: {e}", exc_info=True)

    # Add each entry of file to dictionary:
    envlist = env.split("\n")
    envdict = {}
    for env in envlist:
        if (env == ""):
            continue
        # Map correct value to key:
        envdict[env.split("=")[0]] = env.split("=")[1]

    return envdict