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
  print("## SETUP ##")
  print("# Installing requirements... #")
  ## Install requirements ##
  import subprocess
  log = open("reqlog.txt", "a")
  print("-> pip installs:")
  n = subprocess.run(["pip", "install", '-r', "Sci2XML/app/requirements_final.txt"], stdout=log, stderr=log, text=True)
  print("-> apt-get installs:")
  n = subprocess.run(["apt-get", "install", "poppler-utils"], stdout=log, stderr=log, text=True)
  n = subprocess.run(["apt-get", "install", "-y", "libvips"], stdout=log, stderr=log, text=True)
  print("-> npm installs:")
  n = subprocess.run(["npm", "install", "localtunnel"], stdout=log, stderr=log, text=True)


  ## Launch API ##
  #API()
  # import Sci2XML.app.modules.APIcode as API
  print("# Launching API... #")
  import modules.APIcode as API
  API.API()

  ## Load Grobid and launch Grobid server ##
  #loadGrobid()
  print("# Launching Grobid... #")
  # import Sci2XML.app.modules.grobidmodule as grobidmod
  import modules.grobidmodule as grobidmod
  grobidmod.loadGrobidPythonway()


  ## Start Streamlit and host using Localtunnel ##
  #startStreamlit()
  print("# Starting Streamlit through Localtunnel... #")
  # import Sci2XML.app.modules.frontendmodule as front
  import modules.frontendmodule as front
  front.startStreamlit()



startEverything()
