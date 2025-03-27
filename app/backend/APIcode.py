## API ##
import requests
import os
import sys
import threading
import socket
import albumentations as A
import numpy as np
import nest_asyncio
nest_asyncio.apply()
from flask import Flask, jsonify, make_response, request, Response
from PIL import Image
from tempfile import NamedTemporaryFile
from transformers import DonutProcessor, VisionEncoderDecoderModel, AutoProcessor
from io import BytesIO
from io import StringIO
import time
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

## Our own modules ##
import importlib.util
spec = importlib.util.spec_from_file_location("classifiermodule", "/content/Sci2XML/app/backend/classifier.py")
classifier = importlib.util.module_from_spec(spec)
sys.modules["classifiermodule"] = classifier
spec.loader.exec_module(classifier)
# import Sci2XML.app.modules.classifiermodel as classifier
import backend.models.classifiermodel as classifierML
# import Sci2XML.app.modules.chartparser as charter
import backend.models.chartparser as charter
# import Sci2XML.app.modules.formulaparser as formula
import backend.models.formulaparser as formula
import backend.models.figureparser as figure
import backend.models.tableparser as tableParser

print("\n\n#---------------------- ## Loading models ## -----------------------#\n")
logging.info(f"APIcode - Loading models.")
try:
    # Loading the various parsing models by calling the load function in their module.
    ML = classifierML.loadML()
    charter.load_UniChart()
    formula.load_Sumen()
    figureParserModel, figureParserTokenizer = figure.load()
    logging.info(f"APIcode - Finished loading models.")
except Exception as e:
    logging.error(f"APIcode - An error occurred while loading the models: {e}", exc_info=True)
  


def API(portnr):
  """
  Defines and starts the API.

  Paramaters:
  portnr: The port number the API is hosted on.

  Returns:
  None
  """
  print(socket.gethostbyname(socket.gethostname()))

  app = Flask(__name__)

  @app.route("/")
  def hello():
      return "I am alive!"

  @app.route('/parseFormula', methods=['POST'])
  def handle_formula():
      """
      Endpoint for parsing formulas. It accepts an image file in POST body.

      Paramaters:
      None

      Returns:
      JSON response object
      """
      print("\n")
      logging.info(f"API - parseFormula - You have reached endpoint for formula.")
      
      # Make sure an image is present:
      if 'image' not in request.files:
          return jsonify({"error": "No file uploaded"}), 400

      file = request.files['image']

      # Process image:
      try:
        processedFormulaLaTex, processedFormulaNL = processFormula(file)
        logging.info(f"APIcode - Successfully processed formula.")
      except Exception as e:
        logging.error(f"APIcode - An error occurred while processing formula: {e}", exc_info=True)

      # Return parsed content
      return jsonify({'element_type':"formula", 'formula': processedFormulaLaTex, "NL": processedFormulaNL, "preferred": processedFormulaLaTex})

  @app.route('/parseChart', methods=['POST'])
  def handle_chart():
      """
      Endpoint for parsing charts. It accepts an image file in POST body.

      Paramaters:
      None

      Returns:
      JSON response object
      """
      print("\n")
      logging.info(f"API - parseChart - You have reached endpoint for chart.")

      # Make sure an image is present:
      if 'image' not in request.files:
          return jsonify({"error": "No file uploaded"}), 400

      file = request.files['image']

      # Process image:
      try:
        processedChartCSV, processedChartNL = processChart(file)
        logging.info(f"APIcode - Successfully processed chart.")
      except Exception as e:
        logging.error(f"APIcode - An error occurred while processing chart: {e}", exc_info=True)

      return jsonify({'element_type':"chart", 'NL': processedChartNL, "csv": processedChartCSV, "preferred": processedChartNL})

  @app.route('/parseFigure', methods=['POST'])
  def handle_figure():
      """
      Endpoint for parsing figures. It accepts an image file in POST body.

      Paramaters:
      None

      Returns:
      JSON response object
      """
      print("\n")
      logging.info(f"API - parseFigure - You have reached endpoint for figure.")

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
        logging.info(f"APIcode - parseFigure - prompt: {string_data_prompt}.")
      except Exception as e:
        logging.error(f"APIcode - An error occurred while fetching string value from bytestream: {e}", exc_info=True)


      # Process image:
      try:
        processedFigureNL = processFigure(file, string_data_prompt)
        logging.info(f"APIcode - Successfully processed figure.")
      except Exception as e:
        logging.error(f"APIcode - An error occurred while processing figure: {e}", exc_info=True)

      return jsonify({'element_type':"figure", 'NL': processedFigureNL, "preferred": processedFigureNL})

  @app.route('/parseTable', methods=['POST'])
  def handle_table():
      """
      Endpoint for parsing tables. It accepts an image file in POST body.

      Paramaters:
      None

      Returns:
      JSON response object
      """
      print("\n")
      logging.info(f"API - parseTable - You have reached endpoint for table.")

      # Check if both required files are provided
      if 'pdf' not in request.files or 'grobid_xml' not in request.files:
        return jsonify({"error": "Both PDF and Grobid XML files are required."}), 400

      # Retrieve the uploaded files from the request
      pdf_file = request.files['pdf']
      grobid_xml_file = request.files['grobid_xml']

      # Process image:
      try:
        processedTablesXML = processTable(pdf_file, grobid_xml_file)
        logging.info(f"APIcode - Successfully processed table.")
      except Exception as e:
        logging.error(f"APIcode - An error occurred while processing table: {e}", exc_info=True)

      #Return the final Grobid XML as a downloadable file (with content type "application/xml")
      return Response(
          processedTablesXML,
          mimetype="application/xml",
          headers={"Content-Disposition": "attachment; filename=updated_grobid.xml"}
      )

  def processFormula(file):
      """
      Processes the formula. More specifically redirects to the OCR model.

      Paramaters:
      file: The file/image to be processed.

      Returns:
      latex_code: The generated LaTeX code.
      NLdata: The generated NL data.
      """
      logging.info(f"API - processFormula - processing formula...")
      
      # Ensure proper file
      if file.filename == '':
          return jsonify({"error": "No selected file"}), 400
      image = Image.open(BytesIO(file.read())).convert('RGB')

      # Send to sumen:
      try:
        latex_code = formula.run_sumen_ocr(image)
        logging.info(f"APIcode - Successfully called sumen.")
      except Exception as e:
        logging.error(f"APIcode - An error occurred while calling sumen: {e}", exc_info=True)
      

      NLdata = "some NL"
      return latex_code, NLdata

  def processChart(file):
      """
      Processes the chart. More specifically redirects to the chart model.

      Paramaters:
      file: The file/image to be processed.

      Returns:
      summary: The generated summary.
      table_data: The generated table data.
      """
      logging.info(f"API - processChart - processing chart...")
      
      # Ensure proper file
      if file.filename == '':
          return jsonify({"error": "No selected file"}), 400
      image = Image.open(BytesIO(file.read())).convert('RGB')

      # Send to unichart:
      try:
        summary = charter.generate_unichart_response(image, "<summarize_chart><s_answer>")
        table_data = charter.generate_unichart_response(image, "<extract_data_table><s_answer>")
        structured_table_data = charter.parse_table_data(table_data)
        logging.info(f"APIcode - Successfully called unichart.")
      except Exception as e:
        logging.error(f"APIcode - An error occurred while calling unichart: {e}", exc_info=True)
      
      return structured_table_data, summary

  def processFigure(file, promptContext):
      """
      Processes the figure. More specifically redirects to the VLM model.

      Paramaters:
      image: The file/image to be processed.
      promptContext: A string with the figure description. Can be used to give context to the prompt for the VLM.

      Returns:
      NLdata: The generated NL data.
      """
      logging.info(f"API - processFigure - processing figure...")
      
      # Ensure proper file
      if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

      try:
        # Ensure the image is loaded as a proper PIL Image
        image = Image.open(BytesIO(file.read())).convert('RGB')
      except Exception as e:
        return jsonify({"error": f"Invalid image file: {str(e)}"}), 400

      try:
        answer = figureParserModel.query(image, f"Describe this image deeply. Caption it. Here is the figure description for context: {promptContext}")["answer"]
      except Exception as e:
        return jsonify({"error": f"Model query failed: {str(e)}"}), 500

      NLdata = answer
      return NLdata

  def processTable(pdf_file, grobid_xml_file):
        """
        API endpoint that expects two files:
        - 'pdf': A PDF file to be processed with PDFplumber.
        - 'grobid_xml': A Grobid XML file in which the tables will be replaced.

        Process:
        1. Save the uploaded files temporarily.
        2. Extract tables from the PDF file (using PDFplumber) and get the XML content directly.
        3. Remove existing table figures from the Grobid XML and get the position of the first removed table.
        4. Insert the PDFplumber XML content into the Grobid XML at that position (or append if no tables are found).
        5. Remove empty lines and return the updated Grobid XML as a downloadable file.
        
        Returns:
            Response: A Flask Response object with the updated Grobid XML, served as an XML file.
        """
        logging.info(f"API - processTable - processing table...")
        
        # Save the PDF file temporarily
        with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            pdf_file.save(temp_pdf)
            pdf_path = temp_pdf.name
        # Save the Grobid XML file temporarily
        with NamedTemporaryFile(delete=False, suffix=".xml") as temp_grobid:
            grobid_xml_file.save(temp_grobid)
            grobid_path = temp_grobid.name
        
        # Read the content of the Grobid XML file
        with open(grobid_path, "r", encoding="utf-8") as file:
            grobid_content = file.read()
        
        # Remove existing table figures from the Grobid XML and get the insert position
        grobid_updated, insert_position = tableParser.remove_tables_from_grobid_xml(grobid_path)
        
        # Extract tables from the PDF and obtain the XML content and table count
        pdfplumber_xml, table_count = tableParser.extract_tables_from_pdf(pdf_path)
        
        # Insert the PDFplumber XML content into the Grobid XML content
        final_grobid_xml = tableParser.insert_pdfplumber_content(grobid_updated, pdfplumber_xml, insert_position)
        # Remove any empty lines from the final XML
        final_grobid_xml = tableParser.remove_empty_lines(final_grobid_xml)
        
        # Remove the temporary files
        os.remove(pdf_path)
        os.remove(grobid_path)
        
        data = final_grobid_xml
        return data

  def callVLM(pipe, image, query): # NOT IN USE, WE USE ML FOR CLASSIFICATION INSTEAD.
    """
    Calls the VLM model.

    Paramaters:
    pipe: The VLM model.
    image: The image to be classified.
    query: The query to be used for classification.

    Returns:
    response.text: The response from the VLM model.
    """
    print("\n- Calling VLM -")
    #image = load_image('testimagetext.png')
    image = load_image(image)
    response = pipe((query, image))
    #print(response.text)
    return response.text

  def callML(model, image):
    """
    Calls the ML model that will classify the image.

    Paramaters:
    model: The ML model.
    image: The image to be classified.

    Returns:
    predicted_class_name: The name of the predicted class.
    """
    print(f'callML is running with model: {model} and image: {image}')
    # Load the image
    #image_path = image  # Replace with the path to your image
    #image = Image.open(image_path)
    image = image.convert("RGB")  # Ensure the image is in RGB format

    img_size = 224

    # Define the same transformations used during training
    data_transforms = A.Compose([
        A.Resize(img_size, img_size),
        A.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        A.pytorch.transforms.ToTensorV2()
    ])

    # Apply transformations
    transformed_image = data_transforms(image=np.array(image))["image"]

    # Add a batch dimension
    transformed_image = transformed_image.unsqueeze(0)

    # Move the image to the appropriate device (GPU or CPU)
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    transformed_image = transformed_image.to(device)

    # Make prediction
    predicted_class = model.predict(transformed_image)

    # Get the class name
    class_names = ['just_image', 'bar_chart', 'diagram', 'flow_chart', 'graph',
                  'growth_chart', 'pie_chart', 'table', 'text_sentence']
    predicted_class_name = class_names[predicted_class[0]]

    print(f"Predicted class: {predicted_class_name}")
    return predicted_class_name

 
  @app.route('/callVLM', methods=['POST'])
  def call_vlm(): # NOT IN USE
      print("-- You have reached endpoint for classifier VLM --")

      image = request.files['image']
      image = Image.open(image)

      query = request.files['query']

      ## PROCESS IMAGE
      response = callVLM(VLM, image, query.getvalue().decode("utf-8"))
      #response = "VLMresponse"

      return jsonify({'VLMresponse':response})

  @app.route('/callClassifier', methods=['POST'])
  def call_ml():
      print("\n")
      logging.info(f"API - callClassifier - You have reached endpoint for classifier ML.")

      # Make sure an image is present:
      if 'image' not in request.files:
          return jsonify({"error": "No file uploaded"}), 400

      image = request.files['image']
      image = Image.open(image)

      # Process image:
      try:
        response = classifierML.callML(ML, image)
        logging.info(f"APIcode - Successfully classified image.")
      except Exception as e:
        logging.error(f"APIcode - An error occurred while classifying image: {e}", exc_info=True)


      logging.info(f"API - callClassifier - Predicted class: {response}")

      return jsonify({'ClassifierResponse':response})
  
  @app.route('/process', methods=['POST'])
  def initiate_processing():
      """
      Endpoint for initiating the entire process.
      First reads the uploaded PDF, then sends it to Grobid server.
      Then calls the classifier functions to process the figures and formulas.
      In the end it calls on getXML() and returns the result.

      Paramaters:
      None

      Returns:
      The processed XML file.
      """
      print("\n")
      logging.info(f"API - process - You have reached endpoint for full processing.")
            
      # Make sure an PDF file is present:
      if 'pdffile' not in request.files:
          return jsonify({"error": "No file uploaded"}), 400

      # Opening PDF file:
      file = request.files['pdffile']
      byte_data_PDF = file.read()

      #print("\n----- Saving PDF file... -----")
      #with open("TESTING_temp_pdffile.pdf", "wb") as file:
      #    file.write(byte_data_PDF)

      ## Calling Grobid ##
      logging.info(f"API - process - Calling Grobid.")
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
      # Call grobid server:
      try:
        response = requests.post(grobid_url, files=files, data=params)  # Use 'data' for form-data
        response.raise_for_status()  # Raise exception if status is not 200
        string_data_XML = response.text
        logging.info(f"APIcode - Successfully called Grobid server.")
        # Check if coordinates are missing in the response
        if 'coords' not in response.text:
            logging.warning("APIcode - No coordinates found in PDF file. Please check GROBID settings.")
      except Exception as e:
        logging.error(f"APIcode - An error occurred while calling Grobid server: {e}", exc_info=True)

      ## Table Parser ##
      logging.info(f"API - process - Initiating Table parser.")
      ## Run the xml and pdf through the tableparser before processing further. Could also be done after the processing of the other elements instead.
      # Ready the files
      files = {"grobid_xml": ("xmlfile.xml", string_data_XML, "application/json"), "pdf": ("pdffile.pdf", byte_data_PDF)}

      try:
        # Send to API endpoint for processing of tables
        response = requests.post("http://172.28.0.12:8000/parseTable", files=files)
        string_data_XML = response.text
        logging.info(f'APIcode - Response from table parser: {response}')
      except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while communication with the table parser: {e}", exc_info=True)

      ##  Starting classifier ##
      logging.info(f"API - process - Initiating Classifier.")
      try:
        # Open the XML file and extract all figures and formulas, as well as getting each page of the PDF as an image.
        images, figures, formulas = classifier.openXMLfile(string_data_XML, byte_data_PDF, frontend=False)
        logging.info(f'APIcode - Successfully opened XML file.')
      except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while opening the XML file: {e}", exc_info=True)
      try:
        # Process each figure. The classifier will classify it, send to correct endpoint for processing, and insert response back into XML file.
        classifier.processFigures(figures, images, frontend=False)
        logging.info(f'APIcode - Successfully processed the figures.')
      except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while processeing figures: {e}", exc_info=True)
      try:
        # Process each formula. The classifier will classify it, send to correct endpoint for processing, and insert response back into XML file.
        classifier.processFormulas(formulas, images, mode="regex", frontend=False)
        logging.info(f'APIcode - Successfully processed the formulas.')
      except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while processing formulas: {e}", exc_info=True)


      return str(classifier.getXML(frontend=False))

 

  port = portnr # default 8000
  threading.Thread(target=app.run, kwargs={'host':'0.0.0.0','port':port}).start()