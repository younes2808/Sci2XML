import subprocess
import requests
import re
import getpass
from flask import Flask, jsonify, make_response, request
from pyngrok import ngrok, conf
import time
import logging
import sys
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True,
    handlers=[
        logging.FileHandler("app.log"),  # Log to a file named 'app.log'
        logging.StreamHandler(sys.stdout)  # Also log to console
    ]
)

def startLocaltunnel(port):
  """
  Starts a localtunnel instance and returns the public URL and password.

  Paramaters:
  port: port number to host on.

  Returns:
  tuple: A tuple containing the public URL and password.
  """
  logging.info(f"frontendmodule - Starting Localtunnel.")

  # Get password (which is also the public facing ip adress): 
  res = requests.get('https://ipv4.icanhazip.com')
  passw = res.content.decode('utf8')
  logging.info(f"frontendmodule - Password is: {passw}.")

  # Running localtunnel command:
  #URL = subprocess.run(["npx", "localtunnel", "--port", "8501"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
  URL = subprocess.Popen(["npx", "localtunnel", "--port", port], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
  #URL = subprocess.Popen(["ls"], stdout=subprocess.PIPE)
  logging.info(f"frontendmodule - URL is: {URL}, {URL.stdout.readline}.")
  for line in iter(URL.stdout.readline, ''):
    #print(line)
    match = re.search(r"(https://[a-zA-Z0-9-]+\.loca\.lt)", line)
    if match:
        public_url = match.group(1)
        #print(f"Public URL: {public_url}")
        logging.info(f"frontendmodule - URL Found.")
        break
    else:
      logging.error(f"frontendmodule - Could not find URL.")
      public_url = "URL NOT FOUND"
      break
  print("done")

  return public_url, passw

def startNgrok(port):
  """
  Starts a ngrok instance and returns the public URL and password.

  Paramaters:
  port: port number ngrok should be hosted on.

  Returns:
  tuple: A tuple containing the public URL and password.
  """
  logging.info(f"frontendmodule - Starting Ngrok.")

  # Lets user write their auth token:
  print("Enter your Ngrok Authtoken. Token can be found here: https://dashboard.ngrok.com/get-started/your-authtoken")
  print("Please note: You may need to enter the token and press Enter twice before Ngrok responds.")
  conf.get_default().auth_token = getpass.getpass()

  # Open a ngrok tunnel to the localhost:
  try:
      public_url = ngrok.connect(port).public_url
      print(f" * ngrok tunnel \"{public_url}\" -> \"http://127.0.0.1:{port}\"")
      logging.info(f"frontendmodule - Successfullt opened ngrok tunnel.")
  except Exception as e:
      logging.error(f"frontendmodule - An error occurred while trying to open ngrok tunnel: {e}", exc_info=True)
  
  return public_url, "no password needed"

def startStreamlit(tunnel, portnr):
  """
  Starts a Streamlit application. Then calls on function to start localtunnel.

  Paramaters:
  tunnel: which tunnel provider. Either Localtunnel or Ngrok
  portnr: port number

  Returns:
  None
  """
  logging.info(f"frontendmodule - Starting Streamlit.")
  # Launching streamlit on localhost:
  logfile = open("logs.txt", "w")
  URL = subprocess.Popen(["streamlit", "run", "app/frontend/app.py", "&"], stdout=logfile, stderr=logfile, text=True, cwd="/content/Sci2XML")

  # Exposing localhost through tunnel, depending on which tunnel is selected at launch:
  if (tunnel == "localtunnel"):
    ## Launch Localtunnel ##
    url, passw = startLocaltunnel("8501")
  elif (tunnel == "ngrok"):
    ## Launch Ngrok ##
    url, passw = startNgrok("8501")
  
  # Save url and password to file, in case it doesnt print to console.
  with open("urlpasslog.txt", "w") as file:
    file.write(url)
    file.write("\n")
    file.write(passw)

  print("\n\n############################################################")
  print(f"----->Public URL: {url} \n----->Password: {passw}")
  print("############################################################\n")

def startAPI(tunnel, portnr):
  """
  Starts only the API. Then calls on function to start localtunnel.

  Paramaters:
  tunnel: which tunnel provider. Either Localtunnel or Ngrok
  portnr: port number

  Returns:
  None
  """
  logging.info(f"frontendmodule - Exposing API.")
  logfile = open("logs.txt", "w")

  # Exposing localhost through tunnel, depending on which tunnel is selected at launch:
  if (tunnel == "localtunnel"):
    ## Localtunnel ##
    url, passw = startLocaltunnel(portnr)
  elif (tunnel == "ngrok"):
    ## Ngrok ##
    url, passw = startNgrok(portnr)

  # Save url and password to file, in case it doesnt print to console.
  with open("urlpasslog.txt", "w") as file:
    file.write(url)
    file.write("\n")
    file.write(passw)

  print("\n\n############################################################")
  print(f"----->Public URL: {url} \n----->Password: {passw}")
  print("############################################################\n")