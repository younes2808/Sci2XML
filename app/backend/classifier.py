import requests, json
import io
import re
import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw
from pdf2image import convert_from_path, convert_from_bytes
from pdf2image.exceptions import (
    PDFInfoNotInstalledError,
    PDFPageCountError,
    PDFSyntaxError
)
import logging
import sys
import time
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True,
    handlers=[
        logging.FileHandler("app.log"),  # Log to a file named 'app.log'
        logging.StreamHandler(sys.stdout)  # Also log to console
    ]
)


apiURL = "http://172.28.0.12:8000/"

def openXMLfile(XMLfile, PDFfile, frontend):
    """
    Opens the XML file and converts it to a python dict.

    Paramaters:
    XMLfile: The XML file as stringio object.
    PDFfile: The PDF file as bytes object.
    frontend (bool): Tag stating if frontend is used or not. 

    Returns:
    images: The pages as images from the PDF file.
    figures: The figures from the XML file.
    formulas: The formulas from the XML file.
    """

    #print("\n----- Opening XML and PDF file... -------")
    logging.info("Classifier - Starting function openXMLfile()")

    #stringio = StringIO(XMLfile.getvalue().decode("utf-8"), newline=None)
    #XMLfile = stringio.read()

    # Opening XML file and storing it in variable.
    try:
        global Bs_data
        if (frontend):
            PDFfile = PDFfile.getvalue()
            st.session_state.Bs_data = BeautifulSoup(XMLfile, "xml")
            Bs_data = st.session_state.Bs_data
        else:
            Bs_data = BeautifulSoup(XMLfile, "xml")
        logging.info(f"Classifier - Opened and stored XML and PDF file.")
    except Exception as e:
        logging.error(f"Classifier - An error occurred while opening XML and PDF file: {e}", exc_info=True)

    # Finding all figures and formulas in the xml file using their <figure> or <formula> tag:
    figures = Bs_data.find_all('figure')

    #print("Figures:")
    #print(figures)

    formulas = Bs_data.find_all('formula')

    #print("Formulas:")
    #print(formulas)
    logging.info(f"Classifier - Found all figures and formulas in XML file.")

    # Converting the pages in the PDF file to images.
    try:
        images = convert_from_bytes(PDFfile)
        logging.info(f"Classifier - Converted the pages in the PDF file to images. Found {len(images)} pages/images.")
    except Exception as e:
        images = []
        logging.error(f"Classifier - An error occurred while converting the pages in the PDF file to images: {e}", exc_info=True)

    #for i in range(0, len(images)):
    #    print("--- Image nr ", i+1)

    return images, figures, formulas

def addToXMLfile(type, name, newContent, frontend):
    """
    Adds a new element to the XML file. When a non-textual element has been processed it should be placed back into the XML file at the correct location.

    Paramaters:
    type: The type of the element. (figure or formula)
    name: The name of the element. (fig_# or formula_# where # is the number Grobid gave it.)
    newContent: The new content to be added to the XML file as a dict.
    frontend (bool): Tag stating if frontend is used or not. 

    Returns:
    None
    """
    logging.info("Classifier - Starting function addToXMLfile()")

    ## Find parent tag, and the text content of that:
    try:
        # Find parent tag:
        if (frontend):
            parentTag = st.session_state.Bs_data.find(type, {"xml:id": name})
        else:
            parentTag = Bs_data.find(type, {"xml:id": name})
        logging.info("Classifier - old parentTag: {parentTag}")
        # If there is no parent tag, then there is nowhere to place the content.
        if (parentTag == None):
            logging.error("Classifier - Could not find tag to place element back into...")
            return
        # Try to find all text in the parent tag, but not counting text in child tags:
        textWithoutTag = parentTag.find_all(string=True, recursive=False)
        print("findall", textWithoutTag)
        logging.info("Classifier - find text in tag: {textWithoutTag}")
    except Exception as e:
        parentTag = ""
        textWithoutTag = []
        logging.error(f"Classifier - An error occurred while trying to find parentTag and its content: {e}", exc_info=True)


    ## Add generated content to correct position in new tag
    try:
        if ("formula" in newContent): # Check to see if newContent object has formula key
            newTag = Bs_data.new_tag("latex") # Create new tag
            if (len(textWithoutTag) == 0): # If no text content in tag:
                parentTag.append(newTag) # Add the new tag to parentTag
            else: # If there already is some text in tag (like the Grobids attempt at capturing formula):
                for text in textWithoutTag:
                    if (text in parentTag.contents): # Find the text
                        parentTag.contents[parentTag.contents.index(text)].replace_with(newTag) # Replace text with new tag 
                        textWithoutTag = [] # Make sure it doesnt try to replace the newly inserted tag with another later.
                        break
            newTag.string = newContent["formula"] # Set content of new tag to be the value of object key.
        logging.info(f"Classifier - Successfully added new formula content to parentTag.")
    except Exception as e:
        logging.error(f"Classifier - An error occurred while trying to add new formula content to parentTag: {e}", exc_info=True)
    try:
        if ("NL" in newContent):
            newTag = Bs_data.new_tag("llmgenerated")
            if (len(textWithoutTag) == 0):
                parentTag.append(newTag)
            else:
                for text in textWithoutTag:
                    if (text in parentTag.contents):
                        parentTag.contents[parentTag.contents.index(text)].replace_with(newTag)
                        textWithoutTag = []
                        break
            newTag.string = newContent["NL"]
        logging.info(f"Classifier - Successfully added new llmgenerated content to parentTag.")
    except Exception as e:
        logging.error(f"Classifier - An error occurred while trying to add new llmgenerated content to parentTag: {e}", exc_info=True)
    try:
        if ("csv" in newContent):
            newTag = Bs_data.new_tag("tabledata")
            if (len(textWithoutTag) == 0):
                parentTag.append(newTag)
            else:
                for text in textWithoutTag:
                    if (text in parentTag.contents):
                        parentTag.contents[parentTag.contents.index(text)].replace_with(newTag)
                        textWithoutTag = []
                        break
            newTag.string = str(newContent["csv"])
        logging.info(f"Classifier - Successfully added new csv content to parentTag.")
    except Exception as e:
        logging.error(f"Classifier - An error occurred while trying to add new csv content to parentTag: {e}", exc_info=True)
    

    logging.info("Classifier - new parentTag: {parentTag}")

def getXML(frontend):
   """
   Get function which returns the XML file stored in the variable Bs_data. 

   Paramaters:
   frontend (bool): Tag stating if frontend is used or not. 
   
   Returns:
   Bs_data: The XML file in python dict format.
   """
   logging.info("Classifier - Starting function getXML()")
   if (frontend):
      return st.session_state.Bs_data
   else:
      return Bs_data

def saveXMLfile(pathToXML):
    """
    Saves the XML file to path.

    Paramaters:
    pathToXML: The path to the XML file.

    Returns:
    Bs_data: The XML file in python dict format.
    """
    logging.info("Classifier - Starting function saveXMLfile()")
    try:
        with open(pathToXML, "w", encoding="utf-8") as file:
            file.write(str(Bs_data))
        logging.info(f"Classifier - Successfully saved XML to file.")
        return Bs_data
    except Exception as e:
        logging.error(f"Classifier - An error occurred while trying to save XML file: {e}", exc_info=True)

def classify(XMLtype, image, elementNr, pagenr, regex, PDFelementNr, frontend):
    """
    Classifies a given element as either a formula, chart, figure or other. Based on what the element is classified as 
    it gets redirected to the correct API endpoint for processing. When it gets a response it calls on addToXMLfile() to 
    add the generated content back into the XML. If the frontend tag is set, it also sends the API response to the frontend (app.py)
    so that it can be displayed there.

    Paramaters:
    XMLtype: the type of element. (figure or formula)
    image: the image of the element to be sent to the ML model and for processing.
    elementNr: the number which Grobid gave this figure. Will be used when putting processed content back into the figure tag.
    pagenr: the PDF page number of the element.
    regex: the formula string to be matched against regex.
    PDFelementNr: the correct number for the figure, as it is in the PDF. Might not exist because Grobid finds un-numbered figures/formulas sometimes.
    frontend (bool): Tag stating if frontend is used or not. 

    Returns:
    None
    """
    logging.info("Classifier - Starting function Classifier()")

    ## Redirecting to correct endpoint in API...

    subtype = "unknown"

    ## API request header:
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    APIresponse = ""

    ## Classifying formulas:
    if (XMLtype == "formula"):
      logging.info(f"Classifier - Classifies formula nr:{elementNr}, text: {regex}")
      pattern = r"^(?!\(+$)(?!\)+$).{3,}$"
      ## ^ and $ ensures that the whole string matches.
      ## (?!\(+$) is a negative lookahead that checks that the string doesnt only contain trailing "(".
      ## .{3,} matches any character at least three times, and ensures the string is longer than 2 characters.
      # If the formula meets the criteria for being a formula:
      if (re.match(pattern, regex)):
          #print("YES: ", "Formula: ", elementNr, " ->", regex)
          logging.info(f"Classifier - This formula is indeed a formula.")
          subtype = "formula"
          print("Redirecting to formulaParser")
          ##### APIresponse = API.call("127.0.0.1/formulaParser") #####
          
          # Create a bytes object of the image of the element:
          try:
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            logging.info(f"Classifier - Successfully converted image of element to bytes object.")
          except Exception as e:
            logging.error(f"Classifier - An error occurred while trying create a bytes object of image of element: {e}", exc_info=True)
          
          # Send image of formula to API endpoint where it should be processed by a formula parser:
          try:
            APIresponse = requests.post(apiURL+"parseFormula", files={'image': img_byte_arr})
            APIresponse = APIresponse.json()
            # Set some attributes to the returned response object:
            APIresponse["element_number"] = PDFelementNr
            APIresponse["page_number"] = pagenr
            APIresponse["tag"] = "latex"
            logging.info(f"Classifier - Received response from formulaParser in API.")
          except Exception as e:
            logging.error(f"Classifier - An error occurred while calling API endpoint for formula parser: {e}", exc_info=True)

          #print("Response from formulaParser: --> ", APIresponse["preferred"])
          logging.info(f"Classifier - Response from formulaParser: {APIresponse}")
      # If the formula does not meets the criteria for being a formula:
      else:
          # Not actually a formula, exiting...
          logging.info(f"Classifier - This formula is NOT actually a formula.")
          #print("NO: ", "Formula: ", elementNr, " ->", regex)
          return

    ## Classifying figures:
    else:
      logging.info(f"Classifier - Classifies figure nr:{elementNr}.")

      # Create a bytes object of the image of the element:
      try:
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        logging.info(f"Classifier - Successfully converted image of element to bytes object.")
      except Exception as e:
        logging.error(f"Classifier - An error occurred while trying create a bytes object of image of element: {e}", exc_info=True)

      # Sending image of element to API endpoint for classification:
      try:
        files = {"image": ("image1.png", img_byte_arr)}
        response = requests.post(apiURL+"callClassifier", files=files)
        response = response.json()
        figureClass = response["ClassifierResponse"]
        logging.info(f"Classifier - Received response from API classifier: {figureClass}. Sending it over to the correct API endpoint.")
      except Exception as e:
        logging.error(f"Classifier - An error occurred while calling API endpoint for classification: {e}", exc_info=True)


      ## If the figure is of type 'other':
      # That is, 'just_image' elements are likely elements mistaken as figures, 'table' elements are processed separately and not here, 
      # 'text_sentence' elements are mistakes from Grobid where it captures just raw text sentences or paragraphs as figures.
      if (figureClass.lower() in ["just_image", "table", "text_sentence"]):
        logging.info(f"Classifier - Element identified as 'other' or unknown. Likely a mistake from Grobid. Exiting...")
        return

      ## If the figure is a 'chart':
      if (figureClass.lower() in ['bar_chart', 'diagram', 'graph', 'pie_chart']):
          logging.info(f"Classifier - Element identified as 'chart'. Redirecting to chart parser API endpoint...")
          subtype = figureClass.lower()
          ##### APIresponse = API.call("127.0.0.1/chartParser") #####

          # Create a bytes object of the image of the element:
          try:
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            logging.info(f"Classifier - Successfully converted image of element to bytes object.")
          except Exception as e:
            logging.error(f"Classifier - An error occurred while trying create a bytes object of image of element: {e}", exc_info=True)

          # Send image of figure to API endpoint where it should be processed by a chart parser:
          try:
            APIresponse = requests.post(apiURL+"parseChart", files={'image': img_byte_arr})
            APIresponse = APIresponse.json()
            APIresponse["element_number"] = PDFelementNr
            APIresponse["page_number"] = pagenr
            APIresponse["tag"] = "tabledata"
            logging.info(f"Classifier - Received response from chartParser in API.")
          except Exception as e:
            logging.error(f"Classifier - An error occurred while calling API endpoint for chart parser: {e}", exc_info=True)


          #print("Response from chartParser: --> ", APIresponse["preferred"])
          logging.info(f"Classifier - Response from chartParser: {APIresponse}")

      ## If the figure is a 'figure':
      if (figureClass.lower() in ['flow_chart', 'growth_chart']):
          #print("Redirecting to figureParser. Image identified as ", figureClass.lower())
          logging.info(f"Classifier - Element identified as 'figure'. Redirecting to figure parser API endpoint...")
          subtype = figureClass.lower()
          ##### APIresponse = API.call("127.0.0.1/figureParser") #####

          # Create a bytes object of the image of the element:
          try:
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            logging.info(f"Classifier - Successfully converted image of element to bytes object.")
          except Exception as e:
            logging.error(f"Classifier - An error occurred while trying create a bytes object of image of element: {e}", exc_info=True)

          # Send image of figure to API endpoint where it should be processed by a figure parser:
          try:
            APIresponse = requests.post(apiURL+"parseFigure", files={'image': img_byte_arr})
            APIresponse = APIresponse.json()
            APIresponse["element_number"] = PDFelementNr
            APIresponse["page_number"] = pagenr
            APIresponse["tag"] = "llmgenerated"
            logging.info(f"Classifier - Received response from figureParser in API.")
          except Exception as e:
            logging.error(f"Classifier - An error occurred while calling API endpoint for figure parser: {e}", exc_info=True)


          #print("Response from figureParser: --> ", APIresponse["preferred"])
          logging.info(f"Classifier - Response from figureParser: {APIresponse}")

      ## If the classifier thinks that this figure is a formula:
      # Should not happen often. The main handling of formulas happens at the top of this (classify()) function.
      if ("formula" in figureClass.lower()):
        #print("Redirecting to formulaParser")
        logging.warning(f"Classifier - Element identified as 'formula'. Redirecting to formula parser API endpoint...")
        subtype = "formula"
        ##### APIresponse = API.call("127.0.0.1/formulaParser") #####

        # Create a bytes object of the image of the element:
        try:
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            logging.info(f"Classifier - Successfully converted image of element to bytes object.")
        except Exception as e:
            logging.error(f"Classifier - An error occurred while trying create a bytes object of image of element: {e}", exc_info=True)

        # Send image of formula to API endpoint where it should be processed by a formula parser:
        try:
            APIresponse = requests.post(apiURL+"parseFormula", files={'image': img_byte_arr})
            APIresponse = APIresponse.json()
            APIresponse["element_number"] = PDFelementNr
            APIresponse["page_number"] = pagenr
            APIresponse["tag"] = "latex"
            logging.info(f"Classifier - Received response from formulaParser in API.")
        except Exception as e:
            logging.error(f"Classifier - An error occurred while calling API endpoint for formula parser: {e}", exc_info=True)

        #print("Response from formulaParser: --> ", APIresponse["preferred"])
        logging.info(f"Classifier - Response from formulaParser: {APIresponse}")

    ## If subtype is unknown its better to abort and not add anything back into the XML.
    if (subtype == "unknown"):
      print("Identified as other/unknown. Aborting...")
      logging.info(f"Classifier - Element identified as 'other'/unknown. Exiting...")
      return

    # Call on addToXMLfile() to add the processed content back into the XML file.
    #print("Received response about image nr ", elementNr, ". Will now paste response back into the XML-file.")
    logging.info(f"Classifier - Received response about image nr {elementNr}. Will now paste response back into the XML-file.")
    try:
        if (XMLtype == "figure"):
            addToXMLfile(XMLtype, "fig_" + str(elementNr), APIresponse, frontend)
        elif (XMLtype == "formula"):
            addToXMLfile(XMLtype, "formula_" + str(elementNr), APIresponse, frontend)
        logging.info(f"Classifier - Successfully added content to XML file.")
    except Exception as e:
        logging.error(f"Classifier - An error occurred while calling addToXMLfile(): {e}", exc_info=True)

    
    # If the frontend tag is set, the processed content should be returned to the frontend:
    try: 
        if (frontend):
            ## Uses importlib to find the frontend module:
            import importlib.util
            import sys
            spec = importlib.util.spec_from_file_location("appmodule", "/content/Sci2XML/app/frontend/app.py")
            app = importlib.util.module_from_spec(spec)
            sys.modules["appmodule"] = app
            spec.loader.exec_module(app)
            ## Calls frontend:
            app.processClassifierResponse(APIresponse)
            logging.info(f"Classifier - Successfully called frontend function processClassifierResponse().")
    except Exception as e:
        logging.error(f"Classifier - An error occurred while calling frontend function processClassifierResponse(): {e}", exc_info=True)




def processFigures(figures, images, frontend):
    """
    Crops the figures from the PDF file into images and sends them to the classifier (ML model) for classification.

    Paramaters:
    figures: The figures from the XML file.
    images: The PDF pages as images from the PDF file.
    frontend (bool): Tag stating if frontend is used or not. 

    Returns:
    None
    """
    #print("\n-------- Cropping Figures --------")
    logging.info("Classifier - Starting function processFigures()")

    figurnr = 0 # The number which Grobid gave this figure. Will be used when putting processed content back into the figure tag.
    ## Iterate through all figures:
    for figure in figures:

        ## Getting correct figure number:
        correctFigureNr = 0 # The correct number for the figure, as it is in the PDF. Might not exist because Grobid finds un-numbered figures sometimes.
        try:
            # 1. Try to find <label> tag.
            label = figure.find("label")
            if label is not None:
                if (re.sub("\D", "", label.text) != ""):
                    correctFigureNr = int(re.sub("\D", "", label.text))
                else:
                    # Bad/empty label
                    label = None
            # 2. If the element has no label:
            if label is None:
                #print("NO LABEL")
                logging.info(f"Classifier - There is no <label> tag.")
                # 3. If no label tag, look first for (figurnr) in figure.text:
                compare = re.search(r"\(\d+\)$", figure.text)
                if compare:
                    #print("yay, found figurenr in figuretext using regex")
                    logging.info(f"Classifier - Found figure number in figure text.")
                    correctFigureNr = int(re.sub("\D", "", compare[0]))
                else:
                    # 4. If no label or figurnr in text, try to use <xml:id> tag:
                    #print("nay, could not find figurenr in label or figuretext, using Grobid's number instead...")
                    logging.info(f"Classifier - No figure number in figure text.")
                    if (figure.get("xml:id") != None):
                        correctFigureNr = int(re.sub("\D", "", figure.get("xml:id"))) + 1
                        logging.info(f"Classifier - Found figure nr in <xml:id> tag.")
                    else:
                        # 5. If there is no <label> tag, figurenr in text or a <xml:id> tag, use the self-made self-updated figurenr variable.
                        correctFigureNr = figurnr + 1
                        logging.info(f"Classifier - Using self-made figure number.")
            logging.info(f"Classifier - Successfully found a correct figure number")
        except Exception as e:
            logging.error(f"Classifier - An error occurred while trying to find a correct figure number: {e}", exc_info=True)

            
        #print("----------> FOUND FIGURE NR: ", correctFigureNr)
        logging.info(f"Classifier - Correct figure number is now set as: {correctFigureNr}")

        ## Getting coordinates:
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

        print("----------> FOUND PAGE NR: ", int(coords.split(",")[0]))

        print("\n ---------- Cropping image/figure nr ", figurnr, ". Sending it to ML for classification. ----------")

        ## Saving cropped image to file. Should not be done except for testing.
        # filename = "./MathFormulaImgs/MathFormulafigur" + str(figurnr) + ".png"
        # imgFigur.save(filename)

        ## Sending to classification:

        classify("figure", imgFigur, figurnr, int(coords.split(",")[0]), None, correctFigureNr, frontend)

        figurnr+=1
        #print("----------")

def processFormulas(formulas, images, mode, frontend):
    """
    Crops the formulas from the PDF file into images and sends them to the classifier for classification.

    Paramaters:
    formulas: The formulas from the XML file.
    images: The pages as images from the PDF file.
    mode: The mode to be used for classification. (VLM or regex)
    frontend (bool): Tag stating if frontend is used or not. 

    Returns:
    None
    """
    #print("\n-------- Cropping Formulas ---------")
    logging.info("Classifier - Starting function processFormulas()")

    formulanr = 0 # The number which Grobid gave this formula. Will be used when putting processed content back into the formula tag.
    for formula in formulas:

        ## Getting formula number ##
        correctFigureNr = 0 # The correct number for the formula, as it is in the PDF. Might not exist because Grobid finds un-numbered formulas sometimes.
        label = formula.find("label")
        if label is not None:
            if (re.sub("\D", "", label.text) != ""):
                correctFigureNr = int(re.sub("\D", "", label.text))
            else:
                label = None
        if label is None:
            print("NO LABEL")
            # If no label tag, look for (formulanr) in formula.text
            compare = re.search(r"\(\d+\)$", formula.text)
            if compare:
                correctFigureNr = int(re.sub("\D", "", compare[0]))
            else:
                # If no match, just use xml:id i guess
                correctFigureNr = int(re.sub("\D", "", formula.get("xml:id"))) + 1
        print("----------> FOUND FORMULA NR: ", correctFigureNr)

        ## Getting coords ##
        coords = ""
        try:
            coords = formula.get("coords").split(";")[-1]
        except:
            coords = formula.get("coords")

        imgside = images[int(coords.split(",")[0])-1]

        const = 2.775

        x=float(coords.split(",")[1])
        y=float(coords.split(",")[2])
        x2=float(coords.split(",")[3])
        y2=float(coords.split(",")[4])

        imgFormula = imgside.crop((x*const,y*const,(x+x2)*const,(y+y2)*const))

        print("----------> FOUND PAGE NR: ", int(coords.split(",")[0]))

        print("\n ---------- Cropping image/formula nr ", formulanr, ". Sending it to classifier for classification. ----------")

        ## Saving cropped image to file. Should not be done except for testing.
        # filename = "./MathFormulaImgs/MathFormulaformel" + str(formulanr) + ".png"
        # imgFormula.save(filename)

        ## SENDING TO CLASSIFICATION...

        if (mode == "VLM"):
          classify("formula", imgFormula, formulanr, int(coords.split(",")[0]), None, "Answer with only one word (Yes OR No), is this a formula?", correctFigureNr)
        elif (mode == "regex"):
          classify("formula", imgFormula, formulanr, int(coords.split(",")[0]), formula.text, correctFigureNr, frontend)

        formulanr+=1
        print("----------")
