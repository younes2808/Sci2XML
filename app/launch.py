import time
import argparse
import subprocess
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

def startEverything():
  start_time = time.time()
  time_array = []
  """
  Starts the entire application exposed through frontend. When starting this from the terminal it accepts two arguments: tunnel and port number.
  The port number is the port the API will be hosted on. The tunnel is the tunnel provider which exposes the localhost
  to the outside world. 

  Paramaters:
  None

  Returns:
  None
  """
  print("#----------------------- ################### -----------------------#")
  print("#----------------------- ##### Sci2XML ##### -----------------------#")
  print("#----------------------- ################### -----------------------#\n")
  logging.info("Launch - Starting function startEverything()")
  # Parsing arguments from terminal:
  parser = argparse.ArgumentParser()
  parser.add_argument('--tunnel', dest='tunnel', type=str, help='Set tunnel provider: either localtunnel or ngrok', choices=['localtunnel', 'ngrok', None], default ="ngrok")
  parser.add_argument('--port', dest='port', type=str, help='Set port number', default ="8000")
  args = parser.parse_args()
  logging.info("Launch - Arguments parsed.")

  ## Setup ##
  print("#-------------------------- ### Setup ### --------------------------#\n")
  print("#-------------------- # Installing requirements # ------------------#\n")
  logging.info("Launch - Installing requirements.")
  try:
    log = open("reqlog.txt", "a")
    print("----------> pip installs...")
    n = subprocess.run(["pip", "install", '-r', "Sci2XML/app/requirements_final.txt"], stdout=log, stderr=log, text=True)
    print("----------> apt-get installs...")
    n = subprocess.run(["apt", "update"], stdout=log, stderr=log, text=True)
    n = subprocess.run(["apt-get", "install", "poppler-utils"], stdout=log, stderr=log, text=True)
    n = subprocess.run(["apt-get", "install", "-y", "libvips"], stdout=log, stderr=log, text=True)
    print("----------> npm installs...")
    n = subprocess.run(["npm", "install", "localtunnel"], stdout=log, stderr=log, text=True)
    logging.info(f"Launch - Finished installing requirements.")
  except Exception as e:
      logging.error(f"Launch - An error occurred while trying to install requirements: {e}", exc_info=True)
  
  # Time logging:
  requirements_time = time.time()
  minutes, seconds = divmod(requirements_time - start_time, 60)
  time_array.append({"name": "Installing requirements", "time": requirements_time - start_time})
  logging.info(f"Launch - Installing requirements time: {int(minutes)} minutes and {int(seconds)} seconds")
  print(f"\n-----> Installing requirements time: {int(minutes)} minutes and {int(seconds)} seconds")

  ## Launch API ##
  print("\n\n#----------------- ### Launching API + Models ### ------------------#\n")
  logging.info("Launch - Launching API and models.")
  try:
    import backend.APIcode as API
    API.API(args.port)
    logging.info(f"Launch - Finished launching API and models.")
  except Exception as e:
      logging.error(f"Launch - An error occurred while trying to launch the API and models: {e}", exc_info=True)
  
  # Time logging:
  api_time = time.time() 
  minutes, seconds = divmod(api_time - requirements_time, 60)
  time_array.append({"name": "Launching APIs", "time": api_time - requirements_time})
  logging.info(f"Launching APIs time: {int(minutes)} minutes and {int(seconds)} seconds")
  print(f"\n----->Launching APIs time: {int(minutes)} minutes and {int(seconds)} seconds")

  ## Load Grobid and launch Grobid server ##
  print("\n\n#------------------- ### Load & launch Grobid ### ------------------#\n")
  logging.info("Launch - Loading and launching Grobid.")
  try:
    import backend.grobidmodule as grobidmod
    grobidmod.loadGrobidPythonway()
    logging.info(f"Launch - Finished loading and launching Grobid.")
  except Exception as e:
    logging.error(f"Launch - An error occurred while trying to load and launch Grobid: {e}", exc_info=True)
  
  # Time logging:
  grobid_time = time.time()
  minutes, seconds = divmod(grobid_time - api_time, 60)
  time_array.append({"name": "Launching Grobid", "time": grobid_time - api_time})
  time_array.append({"name": "Total startup", "time": time.time() - start_time})
  logging.info(f"Launching Grobid time: {int(minutes)} minutes and {int(seconds)} seconds")
  print(f"\n----->Launching Grobid time: {int(minutes)} minutes and {int(seconds)} seconds")

  ## Start Streamlit and host using Localtunnel ##
  print("\n\n#------------ ### Starting Streamlit through tunnel ### ------------#\n")
  logging.info(f"Launch - Starting Streamlit through tunnel: {args.tunnel}.")
  try:
    import frontend.frontendmodule as front
    front.startStreamlit(args.tunnel, args.port)
    logging.info(f"Launch - Finished starting Streamlit through tunnel.")
  except Exception as e:
    logging.error(f"Launch - An error occurred while trying to start Streamlit through tunnel: {e}", exc_info=True)
  
  # Time logging:
  print("\n\n")
  for time_object in time_array:
    minutes, seconds = divmod(time_object["time"], 60)
    logging.info(f"{time_object['name']} time: {int(minutes)} minutes and {int(seconds)} seconds")

  print("\n\n#--------------------- ### User Interaction ### --------------------#\n")
  

startEverything()