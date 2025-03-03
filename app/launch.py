def startEverything():
  print("HELOOO")
  """
  Starts the entire application.

  Paramaters:
  None

  Returns:
  None
  """
  ## Setup ##
  ## Install requirements ##
  import subprocess
  log = open("reqlog.txt", "a")
  n = subprocess.run(["pip", "install", '-r', "Sci2XML/app/requirements_final.txt"], stdout=log, stderr=log, text=True)
  log = open("popplerlog.txt", "a")
  n = subprocess.run(["apt-get", "install", "poppler-utils"], stdout=log, stderr=log, text=True)


  ## Launch API ##
  #API()
  import Sci2XML.app.modules.APIcode as API
  API.API()

  ## Load Grobid and launch Grobid server ##
  #loadGrobid()
  import Sci2XML.app.modules.grobidmodule as grobidmod
  grobidmod.loadGrobidPythonway()


  ## Start Streamlit and host using Localtunnel ##
  #startStreamlit()
  import Sci2XML.app.modules.frontendmodule as front
  front.startStreamlit()



startEverything()
