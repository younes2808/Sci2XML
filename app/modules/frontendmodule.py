import subprocess
import requests
import re

import threading
import socket
from flask import Flask, jsonify, make_response, request

def startLocaltunnel():
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
  URL = subprocess.Popen(["npx", "localtunnel", "--port", "8501"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
  #print(URL.stdout.read())

  return public_url, passw

def startStreamlit():
  """
  Starts a Streamlit application. Then calls on function to start localtunnel.

  Paramaters:
  None

  Returns:
  None
  """
  print("Starting Streamlit")
  #!streamlit run app.py &>/content/logs.txt &
  logfile = open("logs.txt", "w")
  URL = subprocess.Popen(["streamlit", "run", "Sci2XML/app/modules/app.py", "&"], stdout=logfile, stderr=logfile, text=True)
  print("Start localtunnel")
  url, passw = startLocaltunnel()
  with open("urlpasslog.txt", "w") as file:
    file.write(url)
    file.write("\n")
    file.write(passw)
  print(f"\n\n Public URL: {url} \n Password: {passw}")