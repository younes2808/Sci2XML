## API ##
import subprocess
import requests
import re
import os

import threading
import socket
from flask import Flask, jsonify, make_response, request, Response
from io import StringIO
from PIL import Image
import io
from tempfile import NamedTemporaryFile

import nest_asyncio
nest_asyncio.apply()

import albumentations as A
import numpy as np

from transformers import DonutProcessor, VisionEncoderDecoderModel, AutoProcessor
from io import BytesIO

## Our own modules ##
#import classifier
import importlib.util
import sys
spec = importlib.util.spec_from_file_location("classifiermodule", "/content/Sci2XML/app/modules/classifier.py")
classifier = importlib.util.module_from_spec(spec)
sys.modules["classifiermodule"] = classifier
spec.loader.exec_module(classifier)
# import Sci2XML.app.modules.classifiermodel as classifier
import modules.classifiermodel as classifierML
# import Sci2XML.app.modules.chartparser as charter
import modules.chartparser as charter
# import Sci2XML.app.modules.formulaparser as formula
import modules.formulaparser as formula
import modules.figureparser as figure
import modules.tableparser as tableParser

ML = classifierML.loadML()
charter.load_UniChart()
formula.load_Sumen()
figureParserModel, figureParserTokenizer = figure.load()

with open("apiinit.txt", "a") as file:
      file.write("\n api init now")

def API():
  """
  Defines and starts the API.

  Paramaters:
  None

  Returns:
  None
  """
  import sys
  #sys.stdout = open("APIlog", "w")

  print(socket.gethostbyname(socket.gethostname()))

  app = Flask(__name__)

  @app.route("/")
  def hello():
      return "I am alive!"

  @app.route('/parseFormula', methods=['POST'])
  def handle_formula():
      print("-- You have reached endpoint for formula --")

      file = request.files['image']

      ## PROCESS IMAGE

      processedFormulaLaTex, processedFormulaNL = processFormula(file)

      return jsonify({'element_type':"formula", 'formula': processedFormulaLaTex, "NL": processedFormulaNL, "preferred": processedFormulaLaTex})

  @app.route('/parseChart', methods=['POST'])
  def handle_chart():
      print("-- You have reached endpoint for chart --")

      file = request.files['image']

      ## PROCESS IMAGE
      processedChartCSV, processedChartNL = processChart(file)

      return jsonify({'element_type':"chart", 'NL': processedChartNL, "csv": processedChartCSV, "preferred": processedChartNL})

  @app.route('/parseFigure', methods=['POST'])
  def handle_figure():
      print("-- You have reached endpoint for figure --")

      file = request.files['image']

      ## PROCESS IMAGE

      processedFigureNL = processFigure(file)

      return jsonify({'element_type':"figure", 'NL': processedFigureNL, "preferred": processedFigureNL})

  @app.route('/parseTable', methods=['POST'])
  def handle_table():
      print("-- You have reached endpoint for table --")

      # Check if both required files are provided
      if 'pdf' not in request.files or 'grobid_xml' not in request.files:
        return jsonify({"error": "Both PDF and Grobid XML files are required."}), 400

      # Retrieve the uploaded files from the request
      pdf_file = request.files['pdf']
      grobid_xml_file = request.files['grobid_xml']

      ## PROCESS TABLES
      # processedTableCSV, processedTableNL = processTable(pdf_file, grobid_xml_file) # Doesnt return a single tabledata+NL, but instead the entire XML with all tables processed.
      processedTablesXML = processTable(pdf_file, grobid_xml_file)

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
      print("Processing formula...")
      ###
      # Send to OCR or something
      ###
      """
      if 'file' not in request.files:
          return jsonify({"error": "No file uploaded"}), 400
      file = request.files['file']
      """
      if file.filename == '':
          return jsonify({"error": "No selected file"}), 400
      image = Image.open(BytesIO(file.read())).convert('RGB')
      latex_code = formula.run_sumen_ocr(image)
      #return jsonify({"latex": latex_code})

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
      print("Processing chart...")

      """
      if 'file' not in request.files:
          return jsonify({"error": "No file uploaded"}), 400
      file = request.files['file']
      """
      if file.filename == '':
          return jsonify({"error": "No selected file"}), 400
      image = Image.open(BytesIO(file.read())).convert('RGB')
      summary = charter.generate_unichart_response(image, "<summarize_chart><s_answer>")
      table_data = charter.generate_unichart_response(image, "<extract_data_table><s_answer>")
      structured_table_data = charter.parse_table_data(table_data)

      return structured_table_data, summary

  def processFigure(file):
      """
      Processes the figure. More specifically redirects to the VLM model.

      Paramaters:
      image: The file/image to be processed.

      Returns:
      NLdata: The generated NL data.
      """
      print("Processing figure...")
      ###
      # Send to VLM or something
      ###
      if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

      try:
        # Ensure the image is loaded as a proper PIL Image
        image = Image.open(BytesIO(file.read())).convert('RGB')
      except Exception as e:
        return jsonify({"error": f"Invalid image file: {str(e)}"}), 400

      try:
        answer = figureParserModel.query(image, "Describe this image deeply. Caption it")["answer"]
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
        print("Processing table...")
        
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

  @app.route("/loadVLM")
  def load_vlm(): # NOT IN USE
      print("API endpoint: Loading VLM...")
      global VLM
      VLM = loadVLM()
      return "API endpoint: Loading VLM..."

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
      print("-- You have reached endpoint for classifier ML --")

      image = request.files['image']
      image = Image.open(image)

      ## PROCESS IMAGE
      response = classifierML.callML(ML, image)
      #response = "VLMresponse"

      return jsonify({'ClassifierResponse':response})
  
  @app.route('/process', methods=['POST'])
  def initiate_processing():
      print("-- You have reached API Endpoint for full processing --")

      ## Opening files: ##
      """
      #  XML file:
      file = request.files['xmlfile']

      stringio = StringIO(file.getvalue().decode("utf-8"), newline=None)
      #with open("testXML.txt", "a") as file:
          #file.write(stringio)
      string_data_XML = stringio.read()

      print("\n----- Saving XML file... -----")
      with open("TESTING_temp_xmlfile.grobid.tei.xml", "w", encoding="utf-8") as file:
          file.write(string_data_XML)
      """
      #  PDF file:
      file = request.files['pdffile']
      byte_data_PDF = file.read()

      print("\n----- Saving PDF file... -----")
      with open("TESTING_temp_pdffile.pdf", "wb") as file:
          file.write(byte_data_PDF)

      ## Calling Grobid ##
      print("-- Calling Grobid --")
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
      response = requests.post(grobid_url, files=files, data=params)  # Use 'data' for form-data
      response.raise_for_status()  # Raise exception if status is not 200
      string_data_XML = response.text

      ## Table Parser ##
      print("-- Table Parser --")
      ### Run the xml and pdf through the tableparser before processing further. Could also be done after the processing of the other elements instead.
      # Ready the files
      files = {"grobid_xml": ("xmlfile.xml", string_data_XML, "application/json"), "pdf": ("pdffile.pdf", byte_data_PDF)}

      # Send to API endpoint for processing of tables
      response = requests.post("http://172.28.0.12:8000/parseTable", files=files)
      print("response", response)
      string_data_XML = response.text

      ##  Starting classifier ##
      print("-- Starting Classifier --")
      images, figures, formulas = classifier.openXMLfile(string_data_XML, byte_data_PDF, frontend=False)
      classifier.processFigures(figures, images, frontend=False)
      classifier.processFormulas(formulas, images, mode="regex", frontend=False)
      # alteredXML = main(string_data_XML, byte_data_PDF)
      #alteredXML = "alteredXML"

      return str(classifier.getXML(frontend=False))
      #   return str(alteredXML)

  @app.route("/test2")
  def test2(): # NOT IN USE
      print("API endpoint: Loading VLM...")
      g = 2
      print("..", g)
      from PIL import Image
      image_path = "chart3.png"  # Replace with the path to your image
      image = Image.open(image_path)
      import modules.classifiermodel as classifierML
      predicted_class_name = classifierML.callML(ML, image)

      print(f"Predicted class: {predicted_class_name}")
      return "API endpoint: Loading VLM..."+str(g) + str(predicted_class_name)

  @app.route('/test', methods=['POST'])
  def test_function(): # NOT IN USE
      text = request.get_json()['text']
      print(text)
      predictions = "predd"
      sentiment = "senttttt"
      return jsonify({'predictions ':predictions, 'sentiment ': sentiment})

  port = 8000
  threading.Thread(target=app.run, kwargs={'host':'0.0.0.0','port':port}).start()