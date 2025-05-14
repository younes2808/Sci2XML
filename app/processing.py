import argparse
import requests
import sys
import logging
import os
from glob import glob # Used to find *.pdf files in folder

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    force=True,
    handlers=[
        logging.FileHandler("app.log"),  # Log to a file named 'app.log'
        logging.StreamHandler(sys.stdout)  # Also log to console
    ]
)

def main():
    """
    Function for initiating the entire process, without the use of frontend.
    First, it reads the uploaded PDF and then sends it to the GROBID server.
    Then, it calls the table parser and classifier functions, which handle all
    formulas, charts, and figures.
    In the end, it calls get_XML() and returns the result.

    Parameters:
    --pdf: Path to a single PDF file.
    --folder: Path to a folder containing multiple PDFs (mutually exclusive with --output).
    --output: Path to save the processed XML file (only used with --pdf).
    --nl_formula: Whether to enable natural language generation for formulas ('True' or 'False').

    Returns:
    The processed XML file(s).
    """

    parser = argparse.ArgumentParser()

    # Arguments
    parser.add_argument('--pdf', dest='pdf', type=str, help='Set path to PDF file.', default="")
    parser.add_argument('--output', dest='path_to_save', type=str, help='Set path to save processed XML file.', default="")
    parser.add_argument('--folder', dest='folder', type=str, help='Set path to a folder containing PDFs.', default="")
    parser.add_argument('--nl_formula', dest='nlformula', type=str, help='Choose if you want NL generated for the formulas.', choices=['True', 'False', None], default="False")

    args = parser.parse_args()

    # Ensure the user doesn't provide both --folder and --output; they are mutually exclusive
    if args.folder and args.path_to_save:
        parser.error("You cannot use --folder and --output together.")

    # Ensure the user provides at least one input source: a single PDF or a folder
    if not args.pdf and not args.folder:
        parser.error("You must provide either --pdf or --folder.")

    # Handle the --nl_formula flag
    if args.nlformula.lower() == "true":
        envdict = get_envdict()

        # If "nl_formula" is missing in the .env, create it with a default value
        if "nl_formula" not in envdict:
            with open("/content/.env", "a") as f:
                f.write("nl_formula=False\n")
            # File is automatically closed after exiting the 'with' block
                
        # Update the value to True and write back to the file
        envdict = get_envdict()
        envdict["nl_formula"] = "True"
        write_envdict(envdict)

    # Ensure runmode is set to "code" in the .env
    envdict = get_envdict()
    if "runmode" not in envdict:
        with open("/content/.env", "a") as f:
            f.write("runmode=frontend\n")
        # File is automatically closed after exiting the 'with' block
            
    envdict = get_envdict()
    envdict["runmode"] = "code"
    write_envdict(envdict)

    # Folder mode: Process all PDFs in the given directory and name output files as 1.xml, 2.xml, etc.
    if args.folder:
        pdf_files = sorted(glob(os.path.join(args.folder, "*.pdf")))
    
        # Get all existing .xml files and extract numeric indices like 1, 2, etc.
        existing_xmls = glob(os.path.join(args.folder, "*.xml"))
        used_indices = [int(os.path.splitext(os.path.basename(f))[0]) for f in existing_xmls if os.path.splitext(os.path.basename(f))[0].isdigit()]
    
        # Start from the next available index
        next_index = max(used_indices, default=0) + 1
    
        for idx, pdf_file in enumerate(pdf_files, start=next_index):
            output_path = os.path.join(args.folder, f"{idx}.xml")
            print(f"\nProcessing {pdf_file} -> {output_path}")
            start_processing(pdf_file, output_path)
    
    # Single PDF mode
    else:
        pdf_path = args.pdf
        path_to_save = args.path_to_save
        base, ext = os.path.splitext(path_to_save)
        count = 1
        final_path = path_to_save
    
        # If the output file already exists, keep adding (1), (2), etc. until it's unique
        while os.path.exists(final_path):
            final_path = f"{base}({count}){ext}"
            count += 1
    
        print(f"\nProcessing single file:")
        print(f"PDF path: {pdf_path}")
        print(f"Output path: {final_path}")
        start_processing(pdf_path, final_path)

def start_processing(pdf_path, path_to_save):
      print("Starting processing")
      """
      Function for initiating the entire process, without the use of frontend.
      First reads the uploaded PDF, then sends it to GROBID server.
      Then calls on table parser. Then calls the classifier functions, which handles all
      formulas, charts and figures.
      In the end it calls on get_XML() and returns the result.

      Paramaters:
      pdf_path: Path to the PDF.

      Returns:
      The processed XML file.
      """
      print("\n")
      logging.info(f"[processing.py] process - You have reached function for full processing.")

      with open(pdf_path, "rb") as f:
        byte_data_PDF = f.read()
      # File is automatically closed after exiting the 'with' block

      ## Calling GROBID ##
      print_update("Calling GROBID")
      logging.info(f"[processing.py] process - Calling GROBID.")
      grobid_url="http://172.28.0.12:8070/api/processFulltextDocument"
      files = {'input': byte_data_PDF}
      params = {
                    "consolidateHeader": 1,
                    "consolidateCitations": 1,
                    "consolidateFunders": 1,
                    "includeRawAffiliations": 1,
                    "includeRawCitations": 1,
                    "segmentSentences": 1,
                    "teiCoordinates": ["ref", "s", "biblStruct", "persName", "figure", "formula", "head", "note", "title", "affiliation"]
                }
      # Call GROBID server:
      try:
        response = requests.post(grobid_url, files=files, data=params)  # Use 'data' for form-data
        response.raise_for_status()  # Raise exception if status is not 200
        string_data_XML = response.text
        logging.info(f"[processing.py] Successfully called GROBID server.")
        
        # Check if coordinates are missing in the response
        if 'coords' not in response.text:
            logging.warning("[processing.py] No coordinates found in PDF file. Please check GROBID settings.")
      except Exception as e:
        logging.error(f"[processing.py] An error occurred while calling GROBID server: {e}", exc_info=True)

      ## Table Parser ##
      print_update("Received response from GROBID, will not initiate Table parser.")
      logging.info(f"[processing.py] process - Initiating Table parser.")
      # Run the xml and pdf through the table parser before processing further. Could also be done after the processing of the other elements instead.
      # Ready the files:
      files = {"grobid_xml": ("xml_file.xml", string_data_XML, "application/json"), "pdf": ("pdf_file.pdf", byte_data_PDF)}

      try:
        # Send to API endpoint for processing of tables
        try:
            envdict = get_envdict()
            
            if ("port" not in envdict): # If key doesnt exist, create it with default value '8000':
                with open("/content/.env", "a") as f:
                    f.write("port=8000\n")
                # File is automatically closed after exiting the 'with' block
            
            envdict = get_envdict()
            port = envdict["port"] # Either what the user selected at launch, or default 8000
            api_url = f"http://172.28.0.12:{port}/" # The URL for the local API.
            logging.info(f"[processing.py] Set URL for api to: {api_url}")
        except Exception as e:
            api_url = "http://172.28.0.12:8000/" # The URL for the local API.
            logging.error(f"[processing.py] An error occurred while setting the port and URL for api: {e}", exc_info=True)
        
        response = requests.post(f"{api_url}parse_table", files=files)
        string_data_XML = response.text
        logging.info(f'[processing.py] Response from table parser: {response}')
      except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while communication with the table parser: {e}", exc_info=True)

      ##  Starting classifier ##
      print_update("Received response from Table parser, will not initiate classification and further processing.")
      logging.info(f"[processing.py] process - Initiating Classifier.")
      
      # Classifier code:
      ## Our own modules ##
      import importlib.util
      
      spec = importlib.util.spec_from_file_location("classifiermodule", "/content/Sci2XML/app/backend/classifier.py")
      classifier = importlib.util.module_from_spec(spec)
      sys.modules["classifiermodule"] = classifier
      spec.loader.exec_module(classifier)
      
      try:
        # Open the XML file and extract all figures and formulas, as well as getting each page of the PDF as an image.
        print_update("Opening XML file and extracting figures and formulas.")
        images, figures, formulas = classifier.open_XML(string_data_XML, byte_data_PDF, frontend=False)
        logging.info(f'[processing.py] Successfully opened XML file.')
      except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while opening the XML file: {e}", exc_info=True)
      
      try:
        # Process each figure. The classifier will classify it, send to correct endpoint for processing, and insert response back into XML file.
        print_update("Processing figures:")
        classifier.process_figures(figures, images, frontend=False)
        logging.info(f'[processing.py] Successfully processed the figures.')
      except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while processeing figures: {e}", exc_info=True)
      
      try:
        # Process each formula. The classifier will classify it, send to correct endpoint for processing, and insert response back into XML file.
        print_update("Processing formulas:")
        classifier.process_formulas(formulas, images, mode="regex", frontend=False)
        logging.info(f'[processing.py] Successfully processed the formulas.')
      except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while processing formulas: {e}", exc_info=True)
      print_update("Processing is finished.")

      altered_xml = str(classifier.get_XML(frontend=False))

      with open(path_to_save, "w") as f:
        f.write(altered_xml)
      # File is automatically closed after exiting the 'with' block
      return altered_xml

def print_update(update):
  print("System Process Update: ", update)

def get_envdict():
    """
    Gets the content of the .env file and creates a dictionary of its elements.

    Parameters:
    None

    Returns:
    envdict (dict): A dictionary with the contents of the .env file.
    """
    # Open and read .env file:
    try:
        with open("/content/.env", "r") as f:
            env = f.read()
        # File is automatically closed after exiting the 'with' block
        logging.info(f"[processing.py] Successfully opened .env file.")
    except Exception as e:
        logging.error(f"[processing.py] An error occurred while opening .env file: {e}", exc_info=True)

    # Add each entry of file to dictionary:
    envlist = env.split("\n")
    envdict = {}
    for env in envlist:
        if (env == ""):
            continue
        # Map correct value to key:
        envdict[env.split("=")[0]] = env.split("=")[1]

    return envdict

def write_envdict(envdict):
  """
  Writes the altered environmentvalues dictionary to .env file.

  Parameters:
  envdict (dict): A dictionary with environment variables.

  Returns:
  None
  """
  try:
    with open("/content/.env", "w") as f:
        # Add each key-value pair in dict to file:
        for key, value in envdict.items():
            f.write(f"{key}={value}\n")
    # File is automatically closed after exiting the 'with' block
    logging.info(f"[processing.py] Successfully saved new content to .env file.")
  except Exception as e:
    logging.error(f"[processing.py] An error occurred while writing new content to .env file: {e}", exc_info=True)

if __name__ == '__main__':
  main()