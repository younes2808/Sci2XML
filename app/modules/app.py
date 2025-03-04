print("Starting Streamlit app...")

import streamlit as st
import requests, json
from PIL import Image
import io
from io import StringIO
import time

#import sys
#sys.stdout = open("streamlitlog", "w")

##### CLASSIFIER ######
# Load modules:

import pandas as pd
from bs4 import BeautifulSoup

from pdf2image import convert_from_path, convert_from_bytes
from pdf2image.exceptions import (
    PDFInfoNotInstalledError,
    PDFPageCountError,
    PDFSyntaxError
)

from PIL import Image, ImageDraw
import os
import json
import time
import requests
import io
import re

#import sys
#sys.stdout = open("classifierlog", "w")

apiURL = "http://172.28.0.12:8000/"

def clean_latex(latex_str):
    # Remove \hskip followed by numbers, pt, and a parenthetical number (allowing for more flexible space handling)
    latex_str = re.sub(r"\\hskip\s*\d+(\.\d+)?\s*pt\s*\(\s*\d+\s*\)\s*", "", latex_str)
    
    # Remove \tag{x} at the end of the expression
    latex_str = re.sub(r"\\tag\s*\{\s*\d+\s*\}\s*", "", latex_str)
    
    # Return the cleaned LaTeX expression
    return latex_str.strip()  # Trim any extra spaces

def openXMLfile(XMLfile, PDFfile):
    """
    Opens the XML file and converts it to a python dict.

    Paramaters:
    XMLfile: The XML file as stringio object.
    PDFfile: The PDF file as bytes object.

    Returns:
    images: The pages as images from the PDF file.
    figures: The figures from the XML file.
    formulas: The formulas from the XML file.
    """

    print("\n----- Opening XML and PDF file... -------")

    #stringio = StringIO(XMLfile.getvalue().decode("utf-8"), newline=None)
    #XMLfile = stringio.read()

    PDFfile = PDFfile.getvalue()

    global Bs_data
    st.session_state.Bs_data = BeautifulSoup(XMLfile, "xml")
    #Bs_data = BeautifulSoup(data, "xml")
    Bs_data = st.session_state.Bs_data

    figures = Bs_data.find_all('figure')

    print("Figures:")
    print(figures)
    st.session_state.metrics["figuresGrobid"] = len(figures)

    formulas = Bs_data.find_all('formula')

    print("Formulas:")
    print(formulas)
    st.session_state.metrics["formulasGrobid"] = len(formulas)

    #images = convert_from_path(pathToPDF, poppler_path='C:\\Program Files\\Release-24.08.0-0\\poppler-24.08.0\\Library\\bin')
    #images = convert_from_path(pathToPDF)
    images = convert_from_bytes(PDFfile)

    for i in range(0, len(images)):
        print("--- Image nr ", i+1)

    return images, figures, formulas


def addToXMLfile(type, name, newContent):
    """
    Adds a new element to the XML file. When a non-textual element has been processed it should be placed back into the XML file at the correct location.

    Paramaters:
    type: The type of the element. (figure or formula)
    name: The name of the element.
    newContent: The new content to be added to the XML file.

    Returns:
    None
    """
    print("\n-- Adding to XML file... --")
    parentTag = st.session_state.Bs_data.find(type, {"xml:id": name})
    print("parentTag: ", parentTag)
    if (parentTag == None):
      print("Could not find tag to place element back into...")
      return
    textWithoutTag = parentTag.find_all(string=True, recursive=False)
    print("findall", textWithoutTag)

    if (len(textWithoutTag) == 0):
        print("Probably a figure...")
        parentTag.append(newContent["preferred"])
    else:
        print("Probably a formula...")
        for text in textWithoutTag:
            if (text in parentTag.contents):
                # print(parentTag.contents.index(text))
                parentTag.contents[parentTag.contents.index(text)].replace_with(newContent["preferred"])

    print(parentTag)


def saveXMLfile(pathToXML):
    """
    FOR TESTING! Saves the XML file.

    Paramaters:
    pathToXML: The path to the XML file.

    Returns:
    Bs_data: The XML file in python dict format.
    """
    print("\n----- Saving XML file... -----")
    with open(pathToXML, "w", encoding="utf-8") as file:
        file.write(str(Bs_data))
    return Bs_data


def classify(XMLtype, image, elementNr, pagenr, regex):
    """
    Classifies a given element as either a formula, table, chart or figure.

    Paramaters:
    XMLtype: the type of element. (figure or formula)
    image: the image to be sent to the VLM model.
    elementNr: the number of the element.
    pagenr: the page number of the element.
    regex: the formula string to be matched against regex.

    Returns:
    None
    """
    print("\n -- Classifier... --")


    ## Redirecting to correct endpoint in API...

    subtype = "unknown"

    ## API request header:
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    APIresponse = ""


    ## For formulas:
    if (XMLtype == "formula"):
      pattern = r"^(?!\(+$)(?!\)+$).{3,}$"
      ## ^ and $ ensures that the whole string matches.
      ## (?!\(+$) is a negative lookahead that checks that the string doesnt only contain trailing "(".
      ## .{3,} matches any character at least three times, and ensures the string is longer than 2 characters.
      if (re.match(pattern, regex)):
          print("YES: ", "Formula: ", elementNr, " ->", regex)
          st.session_state.metrics["formulas"] += 1
          subtype = "formula"
          print("Redirecting to formulaParser")
          ##### APIresponse = API.call("127.0.0.1/formulaParser") #####

          img_byte_arr = io.BytesIO()
          image.save(img_byte_arr, format='PNG')
          img_byte_arr = img_byte_arr.getvalue()

          APIresponse = requests.post(apiURL+"parseFormula", files={'image': img_byte_arr})
          APIresponse = APIresponse.json()
          APIresponse["element_number"] = elementNr
          APIresponse["page_number"] = pagenr

          print("Response from formulaParser: --> ", APIresponse["preferred"])
      else:
          print("NO: ", "Formula: ", elementNr, " ->", regex)
          print("The formula is NOT identified as an actual formula. Aborting...")
          return


    ## For figures:
    else:

      ## When VLM is local:
      #figureClass = callVLM(VLM, image, query)
      ## When VLM is via API:
      img_byte_arr = io.BytesIO()
      image.save(img_byte_arr, format='PNG')
      img_byte_arr = img_byte_arr.getvalue()
      #files = {"image": ("image1.png", img_byte_arr), "query": ("query.txt", query)}
      files = {"image": ("image1.png", img_byte_arr)}
      response = requests.post(apiURL+"callClassifier", files=files)
      print(response.status_code)
      response = response.json()
      print(response)
      figureClass = response["ClassifierResponse"]

      print("Classifier - ML: This image is a -> ", figureClass, " <-    Sending it over to the correct API endpoint")

      ## For 'other':
      if (figureClass.lower() in ["just_image", "table", "text_sentence"]):
        print("Identified as other/unknown. Aborting...")
        return

      ## For charts:
      if (figureClass.lower() in ['bar_chart', 'diagram', 'graph', 'pie_chart']):
          print("Redirecting to chartParser. Image identified as ", figureClass.lower())
          subtype = figureClass.lower()
          st.session_state.metrics["chart"] += 1
          ##### APIresponse = API.call("127.0.0.1/chartParser") #####
          img_byte_arr = io.BytesIO()
          image.save(img_byte_arr, format='PNG')
          img_byte_arr = img_byte_arr.getvalue()

          APIresponse = requests.post(apiURL+"parseChart", files={'image': img_byte_arr})
          APIresponse = APIresponse.json()
          APIresponse["element_number"] = elementNr
          APIresponse["page_number"] = pagenr

          print("Response from chartParser: --> ", APIresponse["preferred"])

      ## For figures:
      if (figureClass.lower() in ['flow_chart', 'growth_chart']):
          print("Redirecting to figureParser. Image identified as ", figureClass.lower())
          subtype = figureClass.lower()
          st.session_state.metrics["figures"] += 1
          ##### APIresponse = API.call("127.0.0.1/figureParser") #####
          img_byte_arr = io.BytesIO()
          image.save(img_byte_arr, format='PNG')
          img_byte_arr = img_byte_arr.getvalue()

          APIresponse = requests.post(apiURL+"parseFigure", files={'image': img_byte_arr})
          APIresponse = APIresponse.json()
          APIresponse["element_number"] = elementNr
          APIresponse["page_number"] = pagenr

          print("Response from figureParser: --> ", APIresponse["preferred"])

      ## For formulas
      if ("formula" in figureClass.lower()):
        print("Redirecting to formulaParser")
        subtype = "formula"
        st.session_state.metrics["formulas"] += 1
        ##### APIresponse = API.call("127.0.0.1/formulaParser") #####
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()

        APIresponse = requests.post(apiURL+"parseFormula", files={'image': img_byte_arr})
        APIresponse = APIresponse.json()
        APIresponse["element_number"] = elementNr
        APIresponse["page_number"] = pagenr

        print("Response from formulaParser: --> ", APIresponse["preferred"])


    ## If subtype is unknown its better to abort and not add anything back into the XML.
    if (subtype == "unknown"):
      print("Identified as other/unknown. Aborting...")
      return


    print("Received response about image nr ", elementNr, ". Will now paste response back into the XML-file.")
    if (XMLtype == "figure"):
      addToXMLfile(XMLtype, "fig_" + str(elementNr), APIresponse)
    elif (XMLtype == "formula"):
      addToXMLfile(XMLtype, "formula_" + str(elementNr), APIresponse)

    ## This writes directly to screen. Is used for testing, should only be added to array instead.
    #st.write(f"Received response about {XMLtype}. It was a {subtype}. APIresponse: {APIresponse}")

    ## Adds to arrays:
    processClassifierResponse(APIresponse)

def processClassifierResponse(APIresponse):
    """
    Processes the response from the classifier and adds it to the correct array.

    Paramaters:
    APIresponse: The response from the classifier as a object/dict. Ex: "{'NL': 'some NL', 'element_type': 'figure', 'preferred': 'some NL', 'element_number': 1, 'page_number': 1}"

    Returns:
    None
    """
    print("Adding to array...")

    #elements = []
    #st.session_state.elements.append(APIresponse)
    element = APIresponse

    #for element in stqdm(elements):
    if element['element_type'] == 'formula':
        st.session_state.formulas_results_array.append(element)
        st.subheader(f"Page {element.get('page_number', 'N/A')}: Formula #{element.get('element_number', 'N/A')}")
        st.markdown(rf"$$ {clean_latex(element.get('formula', 'N/A'))} $$")
        st.text(f"{element.get('NL', 'No description available.')}")

    elif element['element_type'] == "figure":
        st.session_state.figures_results_array.append(element)
        st.subheader(f"Page {element.get('page_number', 'N/A')}: Figure #{element.get('element_number', 'N/A')}")
        st.text(f"{element.get('NL', 'No description available.')}")

    elif element['element_type'] == "chart":
        st.session_state.charts_results_array.append(element)
        st.subheader(f"Page {element.get('page_number', 'N/A')}: Chart #{element.get('element_number', 'N/A')}")
        st.text(f"{element.get('NL', 'No description available.')}")

    elif element['element_type'] == "table":
        st.session_state.tables_results_array.append(element)
        st.subheader(f"Page {element.get('page_number', 'N/A')}: Table #{element.get('element_number', 'N/A')}")
        st.text(f"{element.get('NL', 'No description available.')}")


def processFigures(figures, images):
    """
    Crops the figures from the PDF file into images and sends them to the classifier (ML model) for classification.

    Paramaters:
    figures: The figures from the XML file.
    images: The pages as images from the PDF file.

    Returns:
    None
    """
    print("\n-------- Cropping Figures --------")
    figurnr = 0
    for figure in figures:
        # print("---")
        # print(figure.get("coords"))
        coords = ""
        try:
            coords = figure.get("coords").split(";")[-1]
            # print(coords)
        except:
            coords = figure.get("coords")
            # print(coords)

        imgside = images[int(coords.split(",")[0])-1]

        const = 2.775

        x=float(coords.split(",")[1])
        y=float(coords.split(",")[2])
        x2=float(coords.split(",")[3])
        y2=float(coords.split(",")[4])

        imgFigur = imgside.crop((x*const,y*const,(x+x2)*const,(y+y2)*const))

        print("\n ---------- Cropping image/figure nr ", figurnr, ". Sending it to ML for classification. ----------")

        ## Saving cropped image to file. Should not be done except for testing.
        # filename = "./MathFormulaImgs/MathFormulafigur" + str(figurnr) + ".png"
        # imgFigur.save(filename)

        ## SENDING TO CLASSIFICATION...

        classify("figure", imgFigur, figurnr, int(coords.split(",")[0])-1, None)

        figurnr+=1
        print("----------")

def processFormulas(formulas, images, mode):
    """
    Crops the formulas from the PDF file into images and sends them to the classifier for classification.

    Paramaters:
    formulas: The formulas from the XML file.
    images: The pages as images from the PDF file.
    mode: The mode to be used for classification. (VLM or regex)

    Returns:
    None
    """
    print("\n-------- Cropping Formulas ---------")
    formulanr = 0
    for formula in formulas:
        # print("---")

        coords = ""
        try:
            coords = formula.get("coords").split(";")[-1]
            # print(coords)
        except:
            coords = formula.get("coords")
            # print(coords)

        imgside = images[int(coords.split(",")[0])-1]

        const = 2.775

        x=float(coords.split(",")[1])
        y=float(coords.split(",")[2])
        x2=float(coords.split(",")[3])
        y2=float(coords.split(",")[4])

        imgFormula = imgside.crop((x*const,y*const,(x+x2)*const,(y+y2)*const))

        print("\n ---------- Cropping image/formula nr ", formulanr, ". Sending it to classifier for classification. ----------")

        ## Saving cropped image to file. Should not be done except for testing.
        # filename = "./MathFormulaImgs/MathFormulaformel" + str(formulanr) + ".png"
        # imgFormula.save(filename)

        ## SENDING TO CLASSIFICATION...

        if (mode == "VLM"):
          classify("formula", imgFormula, formulanr, int(coords.split(",")[0])-1, None, "Answer with only one word (Yes OR No), is this a formula?")
        elif (mode == "regex"):
          classify("formula", imgFormula, formulanr, int(coords.split(",")[0])-1, formula.text)

        formulanr+=1
        print("----------")

#----------------------- ##### FRONTEND ##### -----------------------#

#"""
#    This script is a Streamlit-based application that processes PDF files using the GROBID API
#    and provides options to view annotated results for figures and formulas or raw XML data.
#
#    Modules Used:
#    - Streamlit: For building the web interface.
#    - Requests: For making HTTP requests to the GROBID API.
#    - xml.etree.ElementTree: For parsing the XML response from GROBID.
#    - annotated_text: For highlighting elements like figures and formulas.
#    - streamlit_pdf_viewer: For displaying annotated PDFs.
#"""

import streamlit as st
import logging
import os
import re
import math
import sys
import time
import requests
import xml.etree.ElementTree as ET
from streamlit_pdf_viewer import pdf_viewer
from annotated_text import annotated_text, annotation
from stqdm import stqdm
import xml.dom.minidom as minidom

# Configure logging to store logs in a file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),  # Log to a file named 'app.log'
        logging.StreamHandler(sys.stdout)  # Also log to console
    ]
)

def main():
    """
    Main function to handle the Streamlit application logic.
    """
    try:
        st.set_page_config(layout="wide") # Configure the page layout to be wide
        logging.info("Streamlit page configuration set successfully.")
    except Exception as e:
        logging.error(f"Failed to set Streamlit page configuration: {e}", exc_info=True)

    try:
        css_path = os.path.join("Sci2XML/app/modules", "css.html")
        with open(css_path, "r") as f:
            css_content = f.read()
        logging.info(f"CSS file '{css_path}' read successfully.")

        st.markdown(f"{css_content}", unsafe_allow_html=True)
        logging.info("CSS applied to the Streamlit app successfully.")

    except FileNotFoundError:
        logging.error(f"CSS file not found: {css_path}", exc_info=True)
        st.error("CSS file not found. Please check the 'modules' directory.")

    except Exception as e:
        logging.error(f"An error occurred while applying CSS: {e}", exc_info=True)
        st.error("An unexpected error occurred while applying CSS.")

    def process_classifier(xml_input, pdf_file):
        logging.info(f"XML received in classifier:\n{xml_input}")
        logging.info(f"PDF received in classifier:\n{pdf_file}")

        print("------ Starting test run ------")

        ##  Metrics used for benchmarking:
        global metrics
        st.session_state.metrics = {}
        st.session_state.metrics["figuresGrobid"] = 0
        st.session_state.metrics["formulasGrobid"] = 0
        st.session_state.metrics["chart"] = 0
        st.session_state.metrics["formulas"] = 0
        st.session_state.metrics["figures"] = 0
        st.session_state.metrics["tables"] = 0
        st.session_state.metrics["codelistings"] = 0

        if "elements" not in st.session_state or len(st.session_state.elements) != 0:
          st.session_state.elements = []

        # Ensure arrays exist in session state
        if "formulas_results_array" not in st.session_state or len(st.session_state.formulas_results_array) != 0:
            st.session_state.formulas_results_array = []
        if "figures_results_array" not in st.session_state or len(st.session_state.figures_results_array) != 0:
            st.session_state.figures_results_array = []
        if "charts_results_array" not in st.session_state or len(st.session_state.charts_results_array) != 0:
            st.session_state.charts_results_array = []
        if "tables_results_array" not in st.session_state or len(st.session_state.tables_results_array) != 0:
            st.session_state.tables_results_array = []

        images, figures, formulas = openXMLfile(xml_input, pdf_file)
        processFigures(figures, images)
        processFormulas(formulas, images, mode="regex")

        # Convert to string with XML declaration
        xml_string = str(st.session_state.Bs_data)

        st.session_state.interpreted_xml_text = xml_string

        logging.info("Generated XML:\n" + st.session_state.interpreted_xml_text)

    def process_pdf(file, grobid_url="http://172.28.0.12:8070/api/processFulltextDocument", params=None):
        """
        Process a PDF file using the GROBID API and return the response content.

        Parameters:
        file: The PDF file to process.
        grobid_url (str): The URL of the GROBID API endpoint.
        params (dict): Additional parameters for the GROBID request.

        Returns:
        str: The XML content returned by the GROBID API, or None if an error occurred.
        """
        files = {'input': file}
        try:
            # Send request to GROBID
            logging.info(f"Sending file {file} to GROBID")

            response = requests.post(grobid_url, files=files, data=params)  # Use 'data' for form-data
            response.raise_for_status()  # Raise exception if status is not 200

            logging.info(f"Received response from GROBID (status code {response.status_code}).")

            # Check if coordinates are missing in the response
            if 'coords' not in response.text:
                logging.warning("No coordinates found in PDF file. Please check GROBID settings.")
                st.warning("No coordinates found in PDF file. Please check GROBID settings.")

            return response.text  # Return XML or JSON

        except requests.exceptions.RequestException as e:
            logging.error(f"Error while communicating with GROBID: {e}", exc_info=True)
            return None  # Return None on error

    def parse_coords_for_figures(xml_content):
        """
        Extract and parse the 'coords' attribute for <figure> and <formula> elements
        from the GROBID XML output while counting the number of occurrences.

        Parameters:
        xml_content (str): The XML content returned by the GROBID API.

        Returns:
        tuple: A tuple containing:
            - List of annotations with details like page, coordinates, and color.
            - Count of formulas.
            - Count of figures.
        """
        annotations = []

        try:
            logging.info("Parsing PDF file to XML.")

            # Parse the XML content
            namespace = {"tei": "http://www.tei-c.org/ns/1.0"}  # Define the XML namespace
            root = ET.fromstring(xml_content)

            # Find all <figure> and <formula> elements in the XML
            figures = root.findall(".//tei:figure", namespace)
            formulas = root.findall(".//tei:formula", namespace)

            st.session_state.count_figures = len(figures)  # Count figures
            st.session_state.count_formulas = len(formulas)  # Count formulas

            logging.info(f"Found {st.session_state.count_figures} figures and {st.session_state.count_formulas} formulas in PDF file.")

            for figure in figures:
                coords = figure.attrib.get("coords", None)  # Get the 'coords' attribute
                if coords:
                    for group in coords.split(';'):
                        try:
                            values = list(map(float, group.split(',')))
                            if len(values) >= 5:
                                page, x0, y0, x1, y1 = values[:5]
                                annotations.append({
                                    "page": int(page),
                                    "x": float(x0),
                                    "y": float(y0),
                                    "width": x1,
                                    "height": y1,
                                    "color": "#CC0000"
                                })
                        except ValueError as e:
                            logging.warning(f"Error parsing figure group '{group}': {e}")
                            st.warning(f"Error parsing figure group '{group}': {e}")

            for formula in formulas:
                coords = formula.attrib.get("coords", None)  # Get the 'coords' attribute
                if coords:
                    for group in coords.split(';'):
                        try:
                            values = list(map(float, group.split(',')))
                            if len(values) >= 5:
                                page, x0, y0, x1, y1 = values[:5]
                                annotations.append({
                                    "page": int(page),
                                    "x": float(x0),
                                    "y": float(y0),
                                    "width": x1,
                                    "height": y1,
                                    "color": "#0000FF"
                                })
                        except ValueError as e:
                            logging.warning(f"Error parsing formula group '{group}': {e}")
                            st.warning(f"Error parsing formula group '{group}': {e}")

        except ET.ParseError as e:
            logging.error(f"Error parsing XML: {e}", exc_info=True)
            st.error(f"Error parsing XML: {e}")

        logging.info(f"Extraction completed: {len(annotations)} annotations found.")
        return annotations, st.session_state.count_formulas, st.session_state.count_figures

    def update_xml():
        """
        Update the XML content in the session state based on the user's input in the text area.

        Updates:
        st.session_state.xml_text (str): The updated XML content from the text area (st.session_state.xml_editor).

        Parameters & Returns:
        None
        """
        try:
            st.session_state.xml_text = st.session_state.xml_editor  # Update xml_text with the current content in text area
            logging.info(f"Variable xml_text successfully set to the current content in text area.")
        except Exception as e:
            logging.error(f"An error occurred while setting variable xml_text to the current content in text area: {e}", exc_info=True)

    def update_interpreted_xml():
        """
        Update the XML content in the session state based on the user's input in the text area.

        Updates:
        st.session_state.interpreted_xml_text (str): The updated XML content from the text area (st.session_state.interpreted_xml_editor).

        Parameters & Returns:
        None
        """
        try:
            st.session_state.interpreted_xml_text = st.session_state.interpreted_xml_editor  # Update xml_text with the current content in text area
            logging.info(f"Variable interpreted_xml_text successfully set to the current content in text area.")
        except Exception as e:
            logging.error(f"An error occurred while setting variable interpreted_xml_text to the current content in text area: {e}", exc_info=True)

    # Title and logo on the page
    st.image("Sci2XML/app/images/Sci2XML_logo.png")

    # Declare variable
    if 'pdf_ref' not in st.session_state:
        logging.info("Session state: 'pdf_ref' was missing and has been initialized to None.")  # Log initialization

    try:
        # Access the uploaded ref via a key
        uploaded_pdf = st.file_uploader("", type=('pdf'), key='pdf', accept_multiple_files=False)
        logging.info(f"Setting variable uploaded_pdf to be the uploaded PDF file.")
    except Exception as e:
        logging.error(f"An error occurred while setting the variable uploaded_pdf to be the uploaded PDF file: {e}", exc_info=True)

    if uploaded_pdf:
        @st.fragment
        def pdf_upload():
            logging.info("A new PDF file was uploaded.")

            # Reset interpretation results visibility when a new file is uploaded
            if "pdf_ref" in st.session_state and uploaded_pdf != st.session_state.pdf_ref:
                logging.info("Uploaded PDF differs from the stored reference. Resetting interpretation results.")
                st.session_state.show_interpretation_results = False
                st.session_state.xml_text = None
                st.session_state.interpreted_xml_text = None
                st.session_state.results_placeholder = None

            # Backup uploaded file
            st.session_state.pdf_ref = uploaded_pdf
            logging.info("Stored uploaded PDF in session state ('pdf_ref').")

            # Reset pdf_ref when no file is uploaded
            if not st.session_state.pdf:
                logging.warning("No PDF file found in session state. Resetting 'pdf_ref' to None.")
                st.session_state.pdf_ref = None

            # Process binary data if a file is present
            if st.session_state.pdf_ref:
                try:
                    logging.info(f"Extracted binary data from uploaded PDF ({len(st.session_state.pdf_ref.getvalue())} bytes).")
                except Exception as e:
                    logging.error(f"Failed to retrieve binary data from uploaded PDF: {e}", exc_info=True)
                    st.error("An error occurred while reading the uploaded PDF file.")

                # Parameters for GROBID
                params = {
                    "consolidateHeader": 1,
                    "consolidateCitations": 1,
                    "consolidateFunders": 1,
                    "includeRawAffiliations": 1,
                    "includeRawCitations": 1,
                    "segmentSentences": 1,
                    "teiCoordinates": ["ref", "s", "biblStruct", "persName", "figure", "formula", "head", "note", "title", "affiliation"]
                }

                result = None  # Ensure result is always defined

                # Process file as soon as it's uploaded
                with st.status(label="Waiting for GROBID to process the file... 🔄", expanded=False, state="running") as status:
                    result = process_pdf(st.session_state.pdf_ref, params=params)

                    if result is not None and result.startswith("Error when processing file"):
                        st.error(result)
                    else:
                        if result:
                            st.session_state.rectangles, st.session_state.count_formulas, st.session_state.count_figures = parse_coords_for_figures(result)
                        else:
                            st.session_state.rectangles = []
                            st.session_state.count_formulas = 0
                            st.session_state.count_figures = 0
                            result = ""
                    status.update(label="Complete!", state="complete", expanded=False)

                # Initialize the xml_text in session_state if not already set
                if "xml_text" not in st.session_state or st.session_state.xml_text is None:
                    st.session_state.xml_text = result  # Initial XML content from GROBID
                    print(f"xml: {st.session_state.xml_text}")

                if "show_grobid_results" not in st.session_state:
                    st.session_state.show_grobid_results = True  # Set session state flag
                    print(f"grobid result: {st.session_state.show_grobid_results}")

        pdf_upload()

        if st.session_state.show_grobid_results:
        # Layout container to maintain column structure
            with st.container():
                col1, col2, col3 = st.columns([0.45, 0.1, 0.5])  # Ensures both columns have equal width

                with col1:
                    @st.fragment
                    def grobid_results_view():
                        """
                        Render the GROBID results in either PDF View with annotations or raw XML View.
                        """
                        st.header("GROBID Results", divider="gray")  # Always renders first

                        if 'grobid_results_view_option' not in st.session_state:
                            st.session_state.grobid_results_view_option = "PDF 📄"

                        st.session_state.grobid_results_view_option = st.radio("Select View", ["PDF 📄", "XML 📝"], horizontal=True, key='view_toggle', label_visibility="collapsed")

                        # PDF View with annotations
                        if st.session_state.grobid_results_view_option == "PDF 📄":
                            pdf_viewer(input=st.session_state.pdf_ref.getvalue(), height=725, annotations=st.session_state.rectangles, render_text=True, annotation_outline_size=2)
                            if st.session_state.count_formulas > 0 and st.session_state.count_figures > 0:
                                annotated_text(
                                    annotation("Formulas", "", background="#0000FF", color="#FFFFFF"), " ",
                                    annotation("Figures", "", background="#CC0000", color="#FFFFFF")
                                )
                            elif st.session_state.count_formulas > 0:
                                annotated_text(
                                    annotation("Formulas", "", background="#0000FF", color="#FFFFFF")
                                )
                            elif st.session_state.count_figures > 0:
                                annotated_text(
                                    annotation("Figures", "", background="#CC0000", color="#FFFFFF")
                                )

                        # XML View with raw content
                        elif st.session_state.grobid_results_view_option == "XML 📝":
                            # Text area bound to session_state with on_change callback
                            st.text_area(
                                "Edit GROBID XML File",
                                value=st.session_state.xml_text,  # Initial content from session state
                                height=725,
                                key="xml_editor",  # Key for the text area
                                on_change=update_xml,  # Update xml_text when changes are made
                                label_visibility="collapsed" # Hide the label properly
                            )

                    grobid_results_view()

                    @st.fragment
                    def classify2():
                        if st.button("Process file"):
                            with col3:
                                if 'results_placeholder' not in st.session_state or st.session_state.results_placeholder == None:
                                    st.header("Interpretation Results", divider="gray")  # Always stays aligned with col1
                                    st.session_state.results_placeholder = st.empty()
                                    print("results_placeholder created")
                                else:
                                    st.session_state.results_placeholder.empty()
                                    print("results_placeholder emptied")

                                with st.session_state.results_placeholder.container():
                                    if 'interpretation_results_view_option' not in st.session_state:
                                        st.session_state.interpretation_results_view_option = "XML 📝"

                                st.session_state.results_placeholder.empty()

                                # Create a placeholder for the container
                                container_placeholder = st.empty()

                                with container_placeholder.container(height=725, border=True):
                                    process_classifier(st.session_state.xml_text, st.session_state.pdf_ref)  # Use PDF file and updated XML file from session state

                                container_placeholder.empty()

                                with col3:
                                    with st.session_state.results_placeholder.container():
                                        @st.fragment
                                        def interpretation_results_view():
                                            """
                                            Render different interpretation results based on user selection.
                                            """
                                            st.session_state.interpretation_results_view_option = st.radio("Select Non-Textual Element", ["XML 📝", "Formulas 🔢", "Figures 🖼️", "Charts 📊", "Tables 📋"], horizontal=True, key='interpretation_toggle', label_visibility="collapsed")

                                            if st.session_state.interpretation_results_view_option == "XML 📝":
                                                st.text_area(
                                                    "Edit Interpreted XML File",
                                                    value=st.session_state.interpreted_xml_text,  # Initial content from session state
                                                    height=725,
                                                    key="interpreted_xml_editor",  # Key for the text area
                                                    on_change=update_interpreted_xml,  # Update xml_text when changes are made
                                                    label_visibility="collapsed" # Hide the label properly
                                                )

                                            elif st.session_state.interpretation_results_view_option == "Formulas 🔢":
                                                with st.container(height=725, border=True):
                                                    if len(st.session_state.formulas_results_array) > 0:
                                                        for formula in st.session_state.formulas_results_array:  # Use session state variable
                                                            st.subheader(f"Page {formula.get('page_number', 'N/A')}: Formula #{formula.get('element_number', 'N/A')}")
                                                            st.markdown(rf"$$ {clean_latex(formula.get('formula', 'N/A'))} $$")
                                                            st.text(f"{formula.get('NL', 'No description available.')}")
                                                    else:
                                                        st.warning("No formulas detected in PDF file.")

                                            elif st.session_state.interpretation_results_view_option == "Figures 🖼️":
                                                with st.container(height=725, border=True):
                                                    if len(st.session_state.figures_results_array) > 0:
                                                        for figure in st.session_state.figures_results_array:  # Use session state variable
                                                            st.subheader(f"Page {figure.get('page_number', 'N/A')}: Figure #{figure.get('element_number', 'N/A')}")
                                                            st.text(f"{figure.get('NL', 'No description available.')}")
                                                    else:
                                                        st.warning("No figures detected in PDF file.")

                                            elif st.session_state.interpretation_results_view_option == "Charts 📊":
                                                with st.container(height=725, border=True):
                                                    if len(st.session_state.charts_results_array) > 0:
                                                        for chart in st.session_state.charts_results_array:  # Use session state variable
                                                            st.subheader(f"Page {chart.get('page_number', 'N/A')}: Chart #{chart.get('element_number', 'N/A')}")
                                                            st.text(f"{chart.get('NL', 'No description available.')}")
                                                    else:
                                                        st.warning("No charts detected in PDF file.")

                                            elif st.session_state.interpretation_results_view_option == "Tables 📋":
                                                with st.container(height=725, border=True):
                                                    if len(st.session_state.tables_results_array) > 0:
                                                        for table in st.session_state.tables_results_array:  # Use session state variable
                                                            st.subheader(f"Page {table.get('page_number', 'N/A')}: Table #{table.get('element_number', 'N/A')}")
                                                            st.text(f"{table.get('NL', 'No description available.')}")
                                                    else:
                                                        st.warning("No tables detected in PDF file.")

                                            st.download_button(
                                                label="Download XML",
                                                data=st.session_state.interpreted_xml_text.encode("utf-8"),  # Convert text to bytes
                                                file_name="interpreted_results.xml",
                                                mime="application/xml"
                                            )

                                        interpretation_results_view()

                    classify2()
    else:
        # Prompt user to upload a PDF file
        st.write("Upload a PDF file to analyze it in GROBID")

if __name__ == '__main__':
    try:
        logging.info("Calling main function")
        main()
    except Exception as e:
        logging.error(f"Unhandled exception in main: {e}", exc_info=True)
