## API ##
import subprocess
import requests
import re

import threading
import socket
from flask import Flask, jsonify, make_response, request
from io import StringIO
from PIL import Image
import io

import nest_asyncio
nest_asyncio.apply()

import albumentations as A
import numpy as np

from transformers import DonutProcessor, VisionEncoderDecoderModel, AutoProcessor
from io import BytesIO

## Our own modules ##
# import Sci2XML.app.modules.classifiermodel as classifier
import modules.classifiermodel as classifier
# import Sci2XML.app.modules.chartparser as charter
import modules.chartparser as charter
# import Sci2XML.app.modules.formulaparser as formula
import modules.formulaparser as formula
import modules.figureparser as figure

ML = classifier.loadML()
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

      file = request.files['image']

      ## PROCESS IMAGE
      processedTableCSV, processedTableNL = processTable(file)

      return jsonify({'element_type':"table", 'NL': processedTableNL, "csv": processedTableCSV, "preferred": processedTableCSV})

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

  def processTable(image):
      """
      Processes the table. More specifically redirects to the tableParser model.

      Paramaters:
      image: The file/image to be processed.

      Returns:
      CSVdata: The generated CSV table data.
      NLdata: The generated NL data.
      """
      print("Processing table...")
      ###
      # Send to OCR or VLM or tableParser or something
      ###
      CSVdata = ["some CSV data stuff", "22"]
      NLdata = "some NL"
      return CSVdata, NLdata

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
      response = classifier.callML(ML, image)
      #response = "VLMresponse"


      return jsonify({'ClassifierResponse':response})


  @app.route("/test2")
  def test2(): # NOT IN USE
      print("API endpoint: Loading VLM...")
      g = 2
      print("..", g)
      from PIL import Image
      image_path = "chart3.png"  # Replace with the path to your image
      image = Image.open(image_path)
      import modules.classifiermodel as classifier
      predicted_class_name = classifier.callML(ML, image)

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