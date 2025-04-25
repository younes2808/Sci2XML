import time
import argparse
import subprocess
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

def launch():
  start_time = time.time()
  time_array = []
  """
  Starts the entire application exposed only through API. When starting this from the terminal it accepts two arguments: tunnel and port number.
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
  logging.info("[launch_onlyAPI.py] Starting function launch()")
  # Parsing arguments from terminal:
  parser = argparse.ArgumentParser()
  parser.add_argument('--authtoken', dest='authtoken', type=str, help='Set authtoken for Ngrok.', default ="None")
  parser.add_argument('--port', dest='port', type=int, help='Set port number', choices=range(8000, 8070), metavar="[8000-8069]", default =8000)
  parser.add_argument('--nl_formula', dest='nlformula', type=str, help='Choose if you want NL generated for the formulas.', choices=['True', 'False', None], default ="False")
  args = parser.parse_args()
  logging.info("[launch_onlyAPI.py] Arguments parsed.")
  # Set environment variable based on what the user selected on launch. 
  args.port = str(args.port)
  tunnel = "ngrok"
  # Create .env file with the various environment variables:
  with open("/content/.env", "w") as f:
    f.write(f"port={args.port}\n")
    f.write(f"tunnel={tunnel}\n")
    f.write(f"nl_formula={args.nlformula}\n")
    f.write(f"authtoken={args.authtoken}\n")
  # File is automatically closed after exiting the 'with' block

  ## Setup ##
  print("\n#-------------------------- ### Setup ### --------------------------#\n")
  print("#-------------------- # Installing requirements # ------------------#\n")
  logging.info("[launch_onlyAPI.py] Installing requirements.")
  try:
      # Using subprocess to install the pip, apt-get and npm requirements.
      log = open("reqlog.txt", "a")
      print("\n----> pip installs...")
      n = subprocess.run(["pip", "install", '-r', "Sci2XML/app/requirements_final.txt"], stdout=log, stderr=log, text=True)
      print("----> apt-get installs...")
      n = subprocess.run(["apt", "update"], stdout=log, stderr=log, text=True)
      n = subprocess.run(["apt-get", "install", "poppler-utils"], stdout=log, stderr=log, text=True)
      n = subprocess.run(["apt-get", "install", "-y", "libvips"], stdout=log, stderr=log, text=True)
      print("----> npm installs...\n")
      n = subprocess.run(["npm", "install", "localtunnel"], stdout=log, stderr=log, text=True)
      logging.info(f"[launch_onlyAPI.py] Finished installing requirements.")
  except Exception as e:
      logging.error(f"[launch_onlyAPI.py] An error occurred while trying to install requirements: {e}", exc_info=True)
  
  # Time logging:
  requirements_time = time.time()
  minutes, seconds = divmod(requirements_time - start_time, 60)
  time_array.append({"name": "Installing requirements", "time": requirements_time - start_time})
  logging.info(f"[launch_onlyAPI.py] Installing requirements time: {int(minutes)} minutes and {int(seconds)} seconds")
  print(f"\n----> Installing requirements time: {int(minutes)} minutes and {int(seconds)} seconds")

  ## Launch API ##
  print("\n#----------------- ### Launching API + Models ### ------------------#\n")
  logging.info("[launch_onlyAPI.py] Launching API and models.")
  try:
      # When importing the API code, the various models the system uses will also be loaded in now, as the API code is where these models are called on later. 
      import backend.APIcode as API
      API.API(args.port)
      logging.info(f"[launch_onlyAPI.py] Finished launching API and models.")
  except Exception as e:
      logging.error(f"[launch_onlyAPI.py] An error occurred while trying to launch the API and models: {e}", exc_info=True)
  
  # Time logging:
  api_time = time.time() 
  minutes, seconds = divmod(api_time - requirements_time, 60)
  time_array.append({"name": "Launching APIs", "time": api_time - requirements_time})
  logging.info(f"[launch_onlyAPI.py] Launching APIs time: {int(minutes)} minutes and {int(seconds)} seconds")
  print(f"\n---> Launching APIs time: {int(minutes)} minutes and {int(seconds)} seconds")

  ## Load GROBID and launch GROBID server ##
  print("\n#------------------- ### Load & launch GROBID ### ------------------#\n")
  logging.info("[launch_onlyAPI.py] Loading and launching GROBID.")
  try:
      # Import GROBID module. This will also automatically download, install and launch GROBID server.
      import backend.grobidmodule as grobidmod
      grobidmod.load_grobid_python_way()
      logging.info(f"[launch_onlyAPI.py] Finished loading and launching GROBID.")
  except Exception as e:
    logging.error(f"[launch_onlyAPI.py] An error occurred while trying to load and launch GROBID: {e}", exc_info=True)
  
  # Time logging:
  grobid_time = time.time()
  minutes, seconds = divmod(grobid_time - api_time, 60)
  time_array.append({"name": "Launching GROBID", "time": grobid_time - api_time})
  logging.info(f"[launch_onlyAPI.py] Launching GROBID time: {int(minutes)} minutes and {int(seconds)} seconds")
  print(f"\n----> Launching GROBID time: {int(minutes)} minutes and {int(seconds)} seconds")

  ## Start API using tunnel ##
  print("\n#------------ ### Starting API through tunnel ### ------------#\n")
  logging.info(f"[launch_onlyAPI.py] Starting API through tunnel: {tunnel}.")
  try:
      # Import frontendmodule, which will be used to expose localhost to internet.
      import frontend.frontendmodule as front
      # Host frontend through streamlit
      front.start_API(tunnel, args.port)
      logging.info(f"[launch_onlyAPI.py] Finished starting API through tunnel.")
  except Exception as e:
    logging.error(f"[launch_onlyAPI.py] An error occurred while trying to start API through tunnel: {e}", exc_info=True)
  
  # Time logging:
  localtunnel_api_time = time.time()
  minutes, seconds = divmod(localtunnel_api_time - api_time, 60)
  time_array.append({"name": "Launching Localtunnel API", "time": localtunnel_api_time - api_time})
  time_array.append({"name": "Total startup", "time": time.time() - start_time})
  print(f"\n----> Launching Localtunnel API time: {int(minutes)} minutes and {int(seconds)} seconds")

  for time_object in time_array:
    minutes, seconds = divmod(time_object["time"], 60)
    logging.info(f"[launch_onlyAPI.py] {time_object['name']} time: {int(minutes)} minutes and {int(seconds)} seconds")

  try:
    import frontend.frontendmodule as front # Import frontendmodule
    # Retrieve URL and password
    url, passw = front.start_API()
    logging.info(f"[launch.py] Successfully retrieved URL and password from frontendmodule.")
  except Exception as e:
    logging.error(f"[launch.py] An error occurred while trying to retrieve URL and password from frontendmodule: {e}", exc_info=True)
  
  print("\n############################################################")
  print(f"----> Public URL: {url} \n----> Password: {passw}")
  print("############################################################\n")

  print("\n#--------------------- ### User Interaction ### --------------------#\n")

launch()