import subprocess
import requests
import re
import getpass
from flask import Flask, jsonify, make_response, request
from pyngrok import ngrok, conf

def startLocaltunnel(port):
  """
  Starts a localtunnel instance and returns the public URL and password.

  Paramaters:
  None

  Returns:
  tuple: A tuple containing the public URL and password.
  """
  res = requests.get('https://ipv4.icanhazip.com')
  print(res)
  print(res.content.decode('utf8'))
  passw = res.content.decode('utf8')

  #URL = subprocess.run(["npx", "localtunnel", "--port", "8501"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
  URL = subprocess.Popen(["npx", "localtunnel", "--port", port], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
  #URL = subprocess.Popen(["ls"], stdout=subprocess.PIPE)
  print("URL: ", URL)
  print("URL: ", URL.stdout.readline)
  for line in iter(URL.stdout.readline, ''):
    #print(line)
    match = re.search(r"(https://[a-zA-Z0-9-]+\.loca\.lt)", line)
    if match:
        public_url = match.group(1)
        #print(f"Public URL: {public_url}")
        break
    else:
      print("No match found")
      public_url = "URL NOT FOUND"
      break
  print("done")

  return public_url, passw

def startNgrok(port):
  """
  Starts a ngrok instance and returns the public URL and password.

  Paramaters:
  None

  Returns:
  tuple: A tuple containing the public URL and password.
  """

  conf.get_default().auth_token = getpass.getpass()

  # Open a ngrok tunnel to the HTTP server
  public_url = ngrok.connect(port).public_url
  print(f" * ngrok tunnel \"{public_url}\" -> \"http://127.0.0.1:{port}\"")
  return public_url, "ngrok"

def startStreamlit(tunnel, portnr):
  """
  Starts a Streamlit application. Then calls on function to start localtunnel.

  Paramaters:
  tunnel: which tunnel provider. Either Localtunnel or Ngrok
  portnr: port number

  Returns:
  None
  """
  print("Starting Streamlit")
  logfile = open("logs.txt", "w")
  URL = subprocess.Popen(["streamlit", "run", "app/frontend/app.py", "&"], stdout=logfile, stderr=logfile, text=True, cwd="/content/Sci2XML")

  if (tunnel == "localtunnel"):
    ## Launch Localtunnel ##
    print("Start localtunnel")
    url, passw = startLocaltunnel("8501")
  elif (tunnel == "ngrok"):
    ## Launch Ngrok ##
    print("Start ngrok")
    url, passw = startNgrok("8501")
  with open("urlpasslog.txt", "w") as file:
    file.write(url)
    file.write("\n")
    file.write(passw)
  print(f"\n\n Public URL: {url} \n Password: {passw}")

def startAPI(tunnel, portnr):
  """
  Starts only the API. Then calls on function to start localtunnel.

  Paramaters:
  tunnel: which tunnel provider. Either Localtunnel or Ngrok
  portnr: port number

  Returns:
  None
  """
  print("Starting API")
  logfile = open("logs.txt", "w")

  if (tunnel == "localtunnel"):
    ## Localtunnel ##
    print("Start localtunnel")
    url, passw = startLocaltunnel(portnr)
  elif (tunnel == "ngrok"):
    ## Ngrok ##
    print("Start ngrok")
    url, passw = startNgrok(portnr)

  with open("urlpasslog.txt", "w") as file:
    file.write(url)
    file.write("\n")
    file.write(passw)
  print(f"\n\n Public URL: {url} \n Password: {passw}")