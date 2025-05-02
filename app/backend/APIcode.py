## API ##
import requests
import os
import sys
import threading
import logging
import albumentations as A
import nest_asyncio
nest_asyncio.apply()
from flask import Flask, jsonify, make_response, request, Response
from PIL import Image
from tempfile import NamedTemporaryFile
from transformers import DonutProcessor, VisionEncoderDecoderModel, AutoProcessor
from io import BytesIO
from io import StringIO

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    force=True,
    handlers=[
        logging.FileHandler("app.log"),  # Log to a file named 'app.log'
        logging.StreamHandler(sys.stdout)  # Also log to console
    ]
)

# Classifier code:
## Our own modules ##
import importlib.util
spec = importlib.util.spec_from_file_location("classifiermodule", "/content/Sci2XML/app/backend/classifier.py")
classifier = importlib.util.module_from_spec(spec)
sys.modules["classifiermodule"] = classifier
spec.loader.exec_module(classifier)

# Models:
import backend.models.classifiermodel as classifierML
import backend.models.chartparser as charter
import backend.models.formulaparser as formula
import backend.models.figureparser as figure
import backend.models.tableparser as tableParser

print("\n#---------------------- ## Loading models ## -----------------------#\n")
logging.info(f"[APIcode.py] Loading models.")
try:
    # Loading the various parsing models by calling the load function in their module.
    ML = classifierML.load_ml()
    charter.load_unichart()
    formula.load_sumen()
    figureParserModel, figureParserTokenizer = figure.load()
    logging.info(f"[APIcode.py] Finished loading models.")
except Exception as e:
    logging.error(f"[APIcode.py] An error occurred while loading the models: {e}", exc_info=True)

def API(portnr):
  """
  Defines and starts the API.

  Paramaters:
  portnr: The port number the API is hosted on.

  Returns:
  None
  """
  app = Flask(__name__)

  @app.route("/")
  def hello():
      return "I am alive!"

  @app.route('/parse_formula', methods=['POST'])
  def handle_formula():
      """
      Endpoint for parsing formulas. It accepts an image file in POST body.

      Paramaters:
      None

      Returns:
      JSON response object
      """
      print("\n")
      logging.info(f"[APIcode.py] parse_formula - You have reached endpoint for formula.")
      
      # Make sure an image is present:
      if 'image' not in request.files:
          return jsonify({"error": "No file uploaded"}), 400

      file = request.files['image']

      # Process image:
      try:
        processedFormulaLaTex, processedFormulaNL = process_formula(file)
        logging.info(f"[APIcode.py] Successfully processed formula.")
      except Exception as e:
        logging.error(f"[APIcode.py] An error occurred while processing formula: {e}", exc_info=True)

      # Return parsed content
      return jsonify({'element_type':"formula", 'formula': processedFormulaLaTex, "NL": processedFormulaNL, "preferred": processedFormulaLaTex})

  @app.route('/parse_chart', methods=['POST'])
  def handle_chart():
      """
      Endpoint for parsing charts. It accepts an image file in POST body.

      Paramaters:
      None

      Returns:
      JSON response object
      """
      print("\n")
      logging.info(f"[APIcode.py] parse_chart - You have reached endpoint for chart.")

      # Make sure an image is present:
      if 'image' not in request.files:
          return jsonify({"error": "No file uploaded"}), 400

      file = request.files['image']

      # Make sure a prompt is present:
      if 'prompt' not in request.files:
          return jsonify({"error": "No prompt uploaded"}), 400

      prompt = request.files['prompt']
      try:
        # Fetch string value from bytestream
        stringio = StringIO(prompt.getvalue().decode("utf-8"), newline=None)
        string_data_prompt = stringio.read()
        logging.info(f"[APIcode.py] parse_figure - prompt: {string_data_prompt}.")
      except Exception as e:
        logging.error(f"[APIcode.py] An error occurred while fetching string value from bytestream: {e}", exc_info=True)

      # Process image:
      try:
        processedChartCSV, processedChartNL = process_chart(file, string_data_prompt)
        logging.info(f"[APIcode.py] Successfully processed chart.")
      except Exception as e:
        logging.error(f"[APIcode.py] An error occurred while processing chart: {e}", exc_info=True)

      return jsonify({'element_type':"chart", 'NL': processedChartNL, "csv": processedChartCSV, "preferred": processedChartNL})

  @app.route('/parse_figure', methods=['POST'])
  def handle_figure():
      """
      Endpoint for parsing figures. It accepts an image file in POST body.

      Paramaters:
      None

      Returns:
      JSON response object
      """
      print("\n")
      logging.info(f"[APIcode.py] parse_figure - You have reached endpoint for figure.")

      # Make sure an image is present:
      if 'image' not in request.files:
          return jsonify({"error": "No file uploaded"}), 400

      file = request.files['image']

      # Make sure a prompt is present:
      if 'prompt' not in request.files:
          return jsonify({"error": "No prompt uploaded"}), 400

      prompt = request.files['prompt']
      try:
        # Fetch string value from bytestream
        stringio = StringIO(prompt.getvalue().decode("utf-8"), newline=None)
        string_data_prompt = stringio.read()
        logging.info(f"[APIcode.py] parse_figure - prompt: {string_data_prompt}.")
      except Exception as e:
        logging.error(f"[APIcode.py] An error occurred while fetching string value from bytestream: {e}", exc_info=True)

      # Process image:
      try:
        processedFigureNL = process_figures(file, string_data_prompt)
        logging.info(f"[APIcode.py] Successfully processed figure.")
      except Exception as e:
        logging.error(f"[APIcode.py] An error occurred while processing figure: {e}", exc_info=True)

      return jsonify({'element_type':"figure", 'NL': processedFigureNL, "preferred": processedFigureNL})

  @app.route('/parse_table', methods=['POST'])
  def handle_table():
      """
      Endpoint for parsing tables. It accepts an image file in POST body.

      Paramaters:
      None

      Returns:
      JSON response object
      """
      print("\n")
      logging.info(f"[APIcode.py] parse_table - You have reached endpoint for table.")

      # Check if both required files are provided
      if 'pdf' not in request.files or 'grobid_xml' not in request.files:
        return jsonify({"error": "Both PDF and GROBID XML files are required."}), 400

      # Retrieve the uploaded files from the request
      pdf_file = request.files['pdf']
      grobid_xml_file = request.files['grobid_xml']

      # Process image:
      try:
        processedTablesXML = process_table(pdf_file, grobid_xml_file)
        logging.info(f"[APIcode.py] Successfully processed table.")
      except Exception as e:
        logging.error(f"[APIcode.py] An error occurred while processing table: {e}", exc_info=True)

      #Return the final GROBID XML as a downloadable file (with content type "application/xml")
      return Response(
          processedTablesXML,
          mimetype="application/xml",
          headers={"Content-Disposition": "attachment; filename=updated_grobid.xml"}
      )

  def process_formula(file):
      """
      Processes the formula. More specifically redirects to the OCR model.

      Paramaters:
      file: The file/image to be processed.

      Returns:
      latex_code: The generated LaTeX code.
      NLdata: The generated NL data.
      """
      logging.info(f"[APIcode.py] process_formula - processing formula...")
      
      # Ensure proper file
      if file.filename == '':
          return jsonify({"error": "No selected file"}), 400
      image = Image.open(BytesIO(file.read())).convert('RGB')

      # Send to sumen:
      try:
        latex_code = formula.run_sumen_ocr(image)
        logging.info(f"[APIcode.py] Successfully called sumen.")
      except Exception as e:
        logging.error(f"[APIcode.py] An error occurred while calling sumen: {e}", exc_info=True)

      # Create NL for formula:
      try:
        # Check to see if environment variable for NL generation of formula is set and true:
        envdict = get_envdict()
        if ("nl_formula" not in envdict): # If key doesnt exist, create it with default value 'False':
           with open("/content/.env", "a") as f:
              f.write("nl_formula=False\n")
            # File is automatically closed after exiting the 'with' block
        envdict = get_envdict()
        if (envdict["nl_formula"] == "True"):
          logging.info(f"[APIcode.py] Environment variable nl_formula is true, will be generating NL content.")
          prompt = "Describe how the variables in this formula interacts with eachother."
          NLdata = figureParserModel.query(image, prompt)["answer"]
          logging.info(f"[APIcode.py] Successfully called moondream and generated NL.")
        
        else:
          logging.info(f"[APIcode.py] Environment variable nl_formula is false, will not be generating NL content.")
          NLdata = ""
      
      except Exception as e:
        logging.error(f"[APIcode.py] An error occurred while calling moondream and generating NL: {e}", exc_info=True)
        NLdata = ""
      
      return latex_code, NLdata

  def process_chart(file, prompt_context):
      """
      Processes the chart. More specifically redirects to the chart model for extracting tabledata, and call moondream(figureparser) to generate summary.

      Paramaters:
      file: The file/image to be processed.
      prompt_context: A string with the figure description. Can be used to give context to the prompt for the VLM.

      Returns:
      summary: The generated summary.
      table_data: The generated table data.
      """
      logging.info(f"[APIcode.py] process_chart - processing chart...")
      
      # Ensure proper file
      if file.filename == '':
          return jsonify({"error": "No selected file"}), 400
      image = Image.open(BytesIO(file.read())).convert('RGB')

      # Send to UniChart to get parsed tabledata:
      try:
        table_data = charter.generate_unichart_response(image, "<extract_data_table><s_answer>")
        structured_table_data = charter.parse_table_data(table_data)
        logging.info(f"[APIcode.py] Successfully called UniChart.")
      except Exception as e:
        logging.error(f"[APIcode.py] An error occurred while calling UniChart: {e}", exc_info=True)

      # Send to Moondream to get summary of chart:
      try:
        query = f"Describe this chart deeply. Caption it."
        queryWcontext = f"{query} Here is the figure description for context: {prompt_context}"
        
        if (0 < len(prompt_context) < 700): # If the extracted prompt-context is of acceptable length then pass it to model:
          prompt = queryWcontext
        
        else: # If extracted prompt-context is of length 0 or very long then simply do not give the model additional context:
          prompt = query

        logging.info(f"[APIcode.py] Prompt for moonchart used for describing chart: {prompt}.")
        summary = figureParserModel.query(image, prompt)["answer"]
        logging.info(f"[APIcode.py] Successfully called moondream.")
      
      except Exception as e:
        
        return jsonify({"error": f"Model query failed: {str(e)}"}), 500
      
      return structured_table_data, summary

  def process_figures(file, prompt_context):
      """
      Processes the figure. More specifically redirects to the VLM model.

      Paramaters:
      image: The file/image to be processed.
      prompt_context: A string with the figure description. Can be used to give context to the prompt for the VLM.

      Returns:
      NLdata: The generated NL data.
      """
      logging.info(f"[APIcode.py] process_figures - processing figure...")
      
      # Ensure proper file
      if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

      try:
        # Ensure the image is loaded as a proper PIL Image
        image = Image.open(BytesIO(file.read())).convert('RGB')
      
      except Exception as e:
        
        return jsonify({"error": f"Invalid image file: {str(e)}"}), 400

      try:
        if (0 < len(prompt_context) < 700): # If the extracted prompt-context is of acceptable length then pass it to model:
          answer = figureParserModel.query(image, f"Describe and explain this figure with you own words. Here is the figure description for context: '{prompt_context}'")["answer"]
        
        else: # If extracted prompt-context is of length 0 or very long then simply do not give the model additional context:
          answer = figureParserModel.query(image, f"Describe this image deeply. Caption it.")["answer"]
      
      except Exception as e:
        
        return jsonify({"error": f"Model query failed: {str(e)}"}), 500

      NLdata = answer
      return NLdata

  def process_table(pdf_file, grobid_xml_file):
        """
        API endpoint that expects two files:
        - 'pdf': A PDF file to be processed with pdfplumber.
        - 'grobid_xml': A GROBID XML file in which the tables will be replaced.

        Process:
        1. Save the uploaded files temporarily.
        2. Extract tables from the PDF file (using pdfplumber) and get the XML content directly.
        3. Remove existing table figures from the GROBID XML and get the position of the first removed table.
        4. Insert the pdfplumber XML content into the GROBID XML at that position (or append if no tables are found).
        5. Remove empty lines and return the updated GROBID XML as a downloadable file.
        
        Returns:
            Response: A Flask Response object with the updated GROBID XML, served as an XML file.
        """
        logging.info(f"[APIcode.py] process_table - Processing table...")
        
        # Save the PDF file temporarily
        with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            pdf_file.save(temp_pdf)
            pdf_path = temp_pdf.name

        # Save the GROBID XML file temporarily
        with NamedTemporaryFile(delete=False, suffix=".xml") as temp_grobid:
            grobid_xml_file.save(temp_grobid)
            grobid_path = temp_grobid.name
        
        # Read the content of the GROBID XML file
        with open(grobid_path, "r", encoding="utf-8") as file:
            grobid_content = file.read()
        # File is automatically closed after exiting the 'with' block
        
        # Remove existing table figures from the GROBID XML and get the insert position
        grobid_updated, insert_position = tableParser.remove_tables_from_grobid_xml(grobid_path)
        
        # Extract tables from the PDF and obtain the XML content and table count
        pdfplumber_xml, table_count = tableParser.extract_tables_from_pdf(pdf_path)
        
        # Insert the pdfplumber XML content into the GROBID XML content
        final_grobid_xml = tableParser.insert_pdfplumber_content(grobid_updated, pdfplumber_xml, insert_position)
        # Remove any empty lines from the final XML
        final_grobid_xml = tableParser.remove_empty_lines(final_grobid_xml)
        
        # Remove the temporary files
        os.remove(pdf_path)
        os.remove(grobid_path)
        
        data = final_grobid_xml
        return data

  def callVLM(pipe, image, query):
    """
    Calls the InternVL2 VLM model. Not used in current deployment, as we have chosen to use ML model for the classifier and another VLM for the figure parser.

    Paramaters:
    pipe: The VLM model.
    image: The image to be classified.
    query: The query to be used for classification.

    Returns:
    response.text: The response from the VLM model.
    """
    print("\n- Calling VLM -")
    image = load_image(image)
    response = pipe((query, image))
    return response.text
  
  @app.route('/call_classifier', methods=['POST'])
  def call_ml():
      """
      Endpoint for classifying images. It accepts an image file in POST body.

      Paramaters:
      None

      Returns:
      JSON response object
      """
      print("\n")
      logging.info(f"[APIcode.py] call_classifier - You have reached endpoint for classifier ML.")

      # Make sure an image is present:
      if 'image' not in request.files:
          return jsonify({"error": "No file uploaded"}), 400

      image = request.files['image']
      image = Image.open(image)

      # Process image:
      try:
        response = classifierML.call_ml(ML, image)
        logging.info(f"[APIcode.py] Successfully classified image.")
      except Exception as e:
        logging.error(f"[APIcode.py] An error occurred while classifying image: {e}", exc_info=True)

      logging.info(f"[APIcode.py] call_classifier - Predicted class: {response}")

      return jsonify({'classifier_response':response})
  
  @app.route('/process', methods=['POST'])
  def initiate_processing():
      """
      Endpoint for initiating the entire process, without the use of frontend.
      First reads the uploaded PDF, then sends it to GROBID server.
      Then calls on tableparser. Then calls the classifier functions, which handles all
       formulas, charts and figures.
      In the end it calls on get_XML() and returns the result.

      Paramaters:
      None

      Returns:
      The processed XML file.
      """
      print("\n")
      logging.info(f"[APIcode.py] process - You have reached endpoint for full processing.")
            
      # Make sure an PDF file is present:
      if 'pdf_file' not in request.files:
          return jsonify({"error": "No file uploaded"}), 400

      # Opening PDF file:
      file = request.files['pdf_file']
      byte_data_PDF = file.read()

      ## Calling GROBID ##
      logging.info(f"[APIcode.py] process - Calling GROBID.")
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
        logging.info(f"[APIcode.py] Successfully called GROBID server.")
        # Check if coordinates are missing in the response
        if 'coords' not in response.text:
            logging.warning("[APIcode.py] No coordinates found in PDF file. Please check GROBID settings.")
      except Exception as e:
        logging.error(f"[APIcode.py] An error occurred while calling GROBID server: {e}", exc_info=True)

      ## Table Parser ##
      logging.info(f"[APIcode.py] process - Initiating table parser.")
      # Run the xml and pdf through the tableparser before processing further. Could also be done after the processing of the other elements instead.
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
            apiURL = f"http://172.28.0.12:{port}/" # The URL for the local API.
            logging.info(f"[APIcode.py] Set URL for api to: {apiURL}")
        except Exception as e:
            apiURL = "http://172.28.0.12:8000/" # The URL for the local API.
            logging.error(f"[APIcode.py] An error occurred while setting the port and URL for api: {e}", exc_info=True)
        
        response = requests.post(f"{apiURL}parse_table", files=files)
        string_data_XML = response.text
        logging.info(f'[APIcode.py] Response from table parser: {response}')
      except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while communication with the table parser: {e}", exc_info=True)

      ##  Starting classifier ##
      logging.info(f"[APIcode.py] process - Initiating Classifier.")
      try:
        # Open the XML file and extract all figures and formulas, as well as getting each page of the PDF as an image.
        images, figures, formulas = classifier.open_XML(string_data_XML, byte_data_PDF, frontend=False)
        logging.info(f'[APIcode.py] Successfully opened XML file.')
      except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while opening the XML file: {e}", exc_info=True)
      try:
        # Process each figure. The classifier will classify it, send to correct endpoint for processing, and insert response back into XML file.
        classifier.process_figures(figures, images, frontend=False)
        logging.info(f'[APIcode.py] Successfully processed the figures.')
      except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while processeing figures: {e}", exc_info=True)
      try:
        # Process each formula. The classifier will classify it, send to correct endpoint for processing, and insert response back into XML file.
        classifier.process_formulas(formulas, images, mode="regex", frontend=False)
        logging.info(f'[APIcode.py] Successfully processed the formulas.')
      except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while processing formulas: {e}", exc_info=True)

      return str(classifier.get_XML(frontend=False))
  
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
        logging.info(f"[APIcode.py] Successfully opened .env file.")
    except Exception as e:
        logging.error(f"[APIcode.py] An error occurred while opening .env file: {e}", exc_info=True)

    # Add each entry of file to dictionary:
    envlist = env.split("\n")
    envdict = {}
    for env in envlist:
        if (env == ""):
            continue
        # Map correct value to key:
        envdict[env.split("=")[0]] = env.split("=")[1]

    return envdict

  port = portnr # default 8000
  threading.Thread(target=app.run, kwargs={'host':'0.0.0.0','port':port}).start()