import subprocess
import time
import requests
import socket
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    force=True,
    handlers=[
        logging.FileHandler("app.log"),  # Log to a file named 'app.log'
        logging.StreamHandler(sys.stdout)  # Also log to console
    ]
)

def load_grobid_python_way():
  logging.info(f"[grobidmodule.py] Loading GROBID.")

  # First, check if a GROBID server is already running:
  serverstatus = "false"
  try:
    # GET request to the local URL endpoint where the server would be hosted. 
    serverstatus = requests.get('http://172.28.0.12:8070/api/isalive')
    logging.info(f"[grobidmodule.py] GROBID server status: Up.")
    serverstatus = serverstatus.text
  except:
    logging.warning(f"[grobidmodule.py] GROBID server status: Down. No GROBID server is running.")
  
  # Check if GROBID is installed and if the Gradle file exists:
  logging.info(f"[grobidmodule.py] GROBID folder exist: {Path('grobid-0.8.1').is_dir()}")
  logging.info(f"[grobidmodule.py] GROBID Gradlew file exist: {(Path.cwd() / 'grobid-0.8.1' / 'gradlew').exists()}")

  if (serverstatus == "true"):
    # No further actions needed, things are working and the server is up and running.
    logging.info(f"[grobidmodule.py] GROBID server is already running. No futher actions needed.")
    return
  
  if (serverstatus == "false"):
    # Check if GROBID is installed.
    if (Path('grobid-0.8.1').is_dir()) and ((Path.cwd() / 'grobid-0.8.1' / 'gradlew').exists()):
      # GROBID is installed, but server is not running. We then only need to run the 'Gradlew run' command.
      logging.info(f"[grobidmodule.py] GROBID server not running but GROBID exists.")
   
    else:
      # Download and install GROBID, then 'Gradlew run' to start server
      logging.info(f"[grobidmodule.py] GROBID server not running and GROBID doesn't exist. Downloading and installing GROBID with Gradle.")
      print("\n----> Downloading GROBID...\n")
      n = subprocess.run(["wget", "https://github.com/kermitt2/grobid/archive/0.8.1.zip"], stdout=subprocess.PIPE)
      
      print("----> Unzipping GROBID files...")
      n = subprocess.run(["unzip", "0.8.1.zip"], stdout=subprocess.PIPE)
      
      print("----> Installing GROBID with Gradle... (Expected duration: ~4 min)\n")
      grobidinstalllogfile = open("grobidinstalllog.txt", "a")
      n = subprocess.run(["./gradlew", "clean", "install"], stdout=grobidinstalllogfile, stderr=grobidinstalllogfile, text=True, cwd="/content/grobid-0.8.1/")

  # Executing 'gradlew run' command, which should launch the server. This is done with Popen as a 
  #  background command because when the server is up, it doesnt finish the command, but instead just
  #  continues loading and thus halts the application.
  logging.info(f"[grobidmodule.py] Executing command 'gradlew run'.")
  grobidrunlogfile = open("grobidrunlog.txt", "w")
  print("\n----> Launching GROBID server with Gradle:")
  n = subprocess.Popen(["./gradlew", "run"], stdout=grobidrunlogfile, stderr=grobidrunlogfile, text=True, cwd="/content/grobid-0.8.1/")
  # Check grobidrunlog.txt to see when it is ready. Should be > 46 lines when ready.

  print("----> Periodically checking if GROBID server is up yet:")
  clock = -1
  while True:
    if clock == -1:
      print("\nChecking GROBID server status:")
      res = "false"
      
      try:
        res = requests.get('http://172.28.0.12:8070/api/isalive')
      except:
        print("Could not reach GROBID server.")
      print("GROBID server status: Down")
      
      if (res == "false"):
        print("----> GROBID server not up yet, trying again in 5 sec...")
        clock = 5
      
      elif (res.content.decode('utf8') == "true"):
        print("GROBID server status: Up")
        logging.info(f"[grobidmodule.py] GROBID server is up.")
        break
      
      else:
        print("----> GROBID server not up yet, trying again in 5 sec...")
        clock = 5
    sys.stdout.write("\r")
    sys.stdout.write("Trying again in {:2d} seconds.".format(clock)) 
    sys.stdout.flush()
    time.sleep(1)
    clock -= 1

  print("----> GROBID server address: ", socket.gethostbyname(socket.gethostname()), "/8070")