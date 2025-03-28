import subprocess
import time
import requests
import socket
from pathlib import Path
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

def loadGrobidPythonway():
  logging.info(f"grobidmodule - Loading GROBID.")

  # First, check if a GROBID server is already running:
  serverstatus = "false"
  try:
    serverstatus = requests.get('http://172.28.0.12:8070/api/isalive')
    logging.info(f"grobidmodule - Server status. Up: {serverstatus}, {serverstatus.text}")
    serverstatus = serverstatus.text
  except:
    logging.warning(f"grobidmodule - Server status. Up: {serverstatus}. No GROBID server is running.")
  
  # Check if GROBID is installed and if the gradle file exists:
  logging.info(f"grobidmodule - GROBID folder exist: {Path('grobid-0.8.1').is_dir()}")
  logging.info(f"grobidmodule - GROBID gradlew file exist: {(Path.cwd() / 'grobid-0.8.1' / 'gradlew').exists()}")

  if (serverstatus == "true"):
    # No further actions needed, things are working. 
    logging.info(f"grobidmodule - GROBID server is already running. No futher actions needed.")
    return
  if (serverstatus == "false"):
    if (Path('grobid-0.8.1').is_dir()) and ((Path.cwd() / 'grobid-0.8.1' / 'gradlew').exists()):
      # GROBID is installed, but server is not running. We then only need to run the Gradlew run command.
      logging.info(f"grobidmodule - GROBID server not running but GROBID exists.")
    else:
      # Download and install GROBID, then Gradlew run to start server
      logging.info(f"grobidmodule - GROBID server not running and GROBID doesn't exist. Downloading and installing grobid with gradle.")
      print("---> Downloading GROBID...")
      n = subprocess.run(["wget", "https://github.com/kermitt2/grobid/archive/0.8.1.zip"], stdout=subprocess.PIPE)
      
      print("---> Unzipping GROBID files...")
      n = subprocess.run(["unzip", "0.8.1.zip"], stdout=subprocess.PIPE)
      
      print("---> Installing GROBID with gradle... (Expected duration: ∼5 mins)")
      grobidinstalllogfile = open("grobidinstalllog.txt", "a")
      n = subprocess.run(["./gradlew", "clean", "install"], stdout=grobidinstalllogfile, stderr=grobidinstalllogfile, text=True, cwd="/content/grobid-0.8.1/")

  # Executing 'gradlew run' command, which should launch the server. This is done with Popen as a 
  #  background command because when the server is up, it doesnt finish the command, but instead just
  #  continues loading and thus halts the application.
  logging.info(f"grobidmodule - Executing command 'gradlew run'.")
  grobidrunlogfile = open("grobidrunlog.txt", "w")
  print("---> Launching GROBID server with gradle:")
  n = subprocess.Popen(["./gradlew", "run"], stdout=grobidrunlogfile, stderr=grobidrunlogfile, text=True, cwd="/content/grobid-0.8.1/")
  # Check grobidrunlog.txt to see when it is ready. Should be > 46 lines when ready.

  print("---> Periodically checking if GROBID server is up yet:")
  clock = -1
  while True:
    if clock == -1:
      print("\n\nChecking GROBID server status:")
      res = "false"
      try:
        res = requests.get('http://172.28.0.12:8070/api/isalive')
      except:
        print("Could not reach GROBID server.")
      print("Server Status up:", res)
      #print(res.content.decode('utf8'))
      if (res == "false"):
        print("-->GROBID server not up yet, trying again in 5 sec...")
        clock = 5
      elif (res.content.decode('utf8') == "true"):
        print("GROBID server is up!")
        logging.info(f"grobidmodule - GROBID server is up.")
        break
      else:
        print("-->GROBID server not up yet, trying again in 5 sec...")
        clock = 5
    sys.stdout.write("\r")
    sys.stdout.write("Trying again in {:2d} seconds.".format(clock)) 
    sys.stdout.flush()
    time.sleep(1)
    clock -= 1

  #!curl http://172.28.0.12:8070/api/isalive
  print("\nGrobid Server adress: ", socket.gethostbyname(socket.gethostname()), "/8070")