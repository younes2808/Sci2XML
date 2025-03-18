def loadGrobidPythonway():
  import subprocess
  print("Loading Grobid")

  from pathlib import Path
  import requests

  serverstatus = "false"
  try:
    serverstatus = requests.get('http://172.28.0.12:8070/api/isalive')
    print("serverstatus up:", serverstatus, serverstatus.text)
    serverstatus = serverstatus.text
  except:
    print("Error")
  print("serverstatus up:", serverstatus)

  print("Grobid folder exist: ", Path('grobid-0.8.1').is_dir())
  print("Grobid gradlew file exist: ", (Path.cwd() / 'grobid-0.8.1' / 'gradlew').exists())

  if (serverstatus == "true"):
    print("Grobid server is already running.")
    ## No further actions needed, shit is working. 
    return
  if (serverstatus == "false"):
    if (Path('grobid-0.8.1').is_dir()) and ((Path.cwd() / 'grobid-0.8.1' / 'gradlew').exists()):
      print("Grobid server not running but Grobid exists")
      ## Gradlew run to start server
    else:
      print("Grobid server not running and Grobid doesn't exist")
      ## Download and install, then Gradlew run to start server
      n = subprocess.run(["wget", "https://github.com/kermitt2/grobid/archive/0.8.1.zip"], stdout=subprocess.PIPE)

      n = subprocess.run(["unzip", "0.8.1.zip"], stdout=subprocess.PIPE)

      grobidinstalllogfile = open("grobidinstalllog.txt", "a")
      n = subprocess.run(["./gradlew", "clean", "install"], stdout=grobidinstalllogfile, stderr=grobidinstalllogfile, text=True, cwd="/content/grobid-0.8.1/")

  grobidrunlogfile = open("grobidrunlog.txt", "w")
  n = subprocess.Popen(["./gradlew", "run"], stdout=grobidrunlogfile, stderr=grobidrunlogfile, text=True, cwd="/content/grobid-0.8.1/")
  # Check grobidrunlog.txt to see when it is ready. Should be > 46 lines when ready.

  import time
  clock = 0
  while True:
    clock += 1
    print(clock)
    if clock%5 == 0:
      res = "false"
      try:
        res = requests.get('http://172.28.0.12:8070/api/isalive')
      except:
        print("Error")
      print("serverstatus up:", res)
      #print(res.content.decode('utf8'))
      if (res == "false"):
        print("Grobid server not up yet, trying again in 5 sec...")
      elif (res.content.decode('utf8') == "true"):
        print("Grobid server is up!")
        break
      else:
        print("Grobid server not up yet, trying again in 5 sec...")
    time.sleep(1)

  #!curl http://172.28.0.12:8070/api/isalive
  import socket
  print("\n Grobid Server adress: ", socket.gethostbyname(socket.gethostname()), "/8070")