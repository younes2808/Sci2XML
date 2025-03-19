import time
import argparse
import subprocess

def startEverything():
  start_time = time.time()
  time_array = []
  """
  Starts the entire application.

  Paramaters:
  None

  Returns:
  None
  """
  parser = argparse.ArgumentParser()
  parser.add_argument('--tunnel', dest='tunnel', type=str, help='Set tunnel provider: either localtunnel or ngrok', choices=['localtunnel', 'ngrok', None], default ="ngrok")
  parser.add_argument('--port', dest='port', type=str, help='Set port number', default ="8000")
  args = parser.parse_args()

  ## Setup ##
  print("## SETUP ##")
  print("# Installing requirements... #")
  log = open("reqlog.txt", "a")
  print("-> pip installs:")
  n = subprocess.run(["pip", "install", '-r', "Sci2XML/app/requirements_final.txt"], stdout=log, stderr=log, text=True)
  print("-> apt-get installs:")
  n = subprocess.run(["apt", "update"], stdout=log, stderr=log, text=True)
  n = subprocess.run(["apt-get", "install", "poppler-utils"], stdout=log, stderr=log, text=True)
  n = subprocess.run(["apt-get", "install", "-y", "libvips"], stdout=log, stderr=log, text=True)
  print("-> npm installs:")
  n = subprocess.run(["npm", "install", "localtunnel"], stdout=log, stderr=log, text=True)

  requirements_time = time.time()
  minutes, seconds = divmod(requirements_time - start_time, 60)
  time_array.append({"name": "Installing requirements", "time": requirements_time - start_time})
  print(f"Installing requirements time: {int(minutes)} minutes and {int(seconds)} seconds")

  ## Launch API ##
  print("# Launching API... #")
  import modules.APIcode as API
  API.API(args.port)

  api_time = time.time() 
  minutes, seconds = divmod(api_time - requirements_time, 60)
  time_array.append({"name": "Launching APIs", "time": api_time - requirements_time})
  print(f"Launching APIs time: {int(minutes)} minutes and {int(seconds)} seconds")

  ## Load Grobid and launch Grobid server ##
  print("# Launching Grobid... #")
  import modules.grobidmodule as grobidmod
  grobidmod.loadGrobidPythonway()

  grobid_time = time.time()
  minutes, seconds = divmod(grobid_time - api_time, 60)
  time_array.append({"name": "Launching Grobid", "time": grobid_time - api_time})
  time_array.append({"name": "Total startup", "time": time.time() - start_time})
  print(f"Launching Grobid time: {int(minutes)} minutes and {int(seconds)} seconds")

  ## Start Streamlit and host using Localtunnel ##
  print("# Starting Streamlit through Localtunnel... #")
  import modules.frontendmodule as front
  front.startStreamlit(args.tunnel, args.port)

  for time_object in time_array:
    minutes, seconds = divmod(time_object["time"], 60)
    print(f"{time_object['name']} time: {int(minutes)} minutes and {int(seconds)} seconds")

startEverything()