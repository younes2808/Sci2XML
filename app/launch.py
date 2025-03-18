import time

def startEverything():
  start_time = time.time()
  """
  Starts the entire application.

  Paramaters:
  None

  Returns:
  None
  """
  import argparse

  parser = argparse.ArgumentParser()
  parser.add_argument('--tunnel', dest='tunnel', type=str, help='Set tunnel provider: either localtunnel or ngrok', choices=['localtunnel', 'ngrok', None], default ="ngrok")
  parser.add_argument('--port', dest='port', type=str, help='Set port number', default ="8000")
  args = parser.parse_args()

  ## Setup ##
  print("## SETUP ##")
  print("# Installing requirements... #")
  ## Install requirements ##
  import subprocess
  log = open("reqlog.txt", "a")
  print("-> pip installs:")
  n = subprocess.run(["pip", "install", '-r', "Sci2XML/app/requirements_final.txt"], stdout=log, stderr=log, text=True)
  print("-> apt-get installs:")
  n = subprocess.run(["apt", "update"], stdout=log, stderr=log, text=True)
  n = subprocess.run(["apt-get", "install", "poppler-utils"], stdout=log, stderr=log, text=True)
  n = subprocess.run(["apt-get", "install", "-y", "libvips"], stdout=log, stderr=log, text=True)
  print("-> npm installs:")
  n = subprocess.run(["npm", "install", "localtunnel"], stdout=log, stderr=log, text=True)

  ## Launch API ##
  print("# Launching API... #")
  import modules.APIcode as API
  API.API(args.port)

  ## Load Grobid and launch Grobid server ##
  print("# Launching Grobid... #")
  import modules.grobidmodule as grobidmod
  grobidmod.loadGrobidPythonway()

  ## Start Streamlit and host using Localtunnel ##
  print("# Starting Streamlit through Localtunnel... #")
  import modules.frontendmodule as front
  front.startStreamlit(args.tunnel, args.port)

  end_time = time.time()  # End the timer
  elapsed_time = end_time - start_time
  minutes, seconds = divmod(elapsed_time, 60)
  print(f"Total startup time: {int(minutes)} minutes and {int(seconds)} seconds")

startEverything()