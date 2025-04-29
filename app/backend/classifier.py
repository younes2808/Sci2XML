# Imports:
import requests
import io
import re
import os
import streamlit as st
import logging
import sys
import logging
from bs4 import BeautifulSoup # For parsing XML and HTML documents
from PIL import Image, ImageDraw
from pdf2image import convert_from_path, convert_from_bytes # Module which turns each page of a PDF into an image.
from pdf2image.exceptions import ( # Built-in exception handlers. 
    PDFInfoNotInstalledError,
    PDFPageCountError,
    PDFSyntaxError
)

# Set configuration for logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    force=True,
    handlers=[
        logging.FileHandler("app.log"),  # Log to a file named 'app.log'
        logging.StreamHandler(sys.stdout)  # Also log to console
    ]
)

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
        logging.info(f"[classifier.py] Successfully opened .env file.")
    except Exception as e:
        logging.error(f"[classifier.py] An error occurred while opening .env file: {e}", exc_info=True)

    # Add each entry of file to dictionary:
    envlist = env.split("\n")
    envdict = {}
    for env in envlist:
        if (env == ""):
            continue
        # Map correct value to key:
        envdict[env.split("=")[0]] = env.split("=")[1]

    return envdict

try:
    envdict = get_envdict()
    if ("port" not in envdict): # If key doesnt exist, create it with default value '8000':
        with open("/content/.env", "a") as f:
            f.write("port=8000\n")
        # File is automatically closed after exiting the 'with' block
    envdict = get_envdict()
    port = envdict["port"] # Either what the user selected at launch, or default 8000
    apiURL = f"http://172.28.0.12:{port}/" # The URL for the local API.
    logging.info(f"[classifier.py] Set URL for api to: {apiURL}")
except Exception as e:
    apiURL = "http://172.28.0.12:8000/" # The URL for the local API.
    logging.error(f"[classifier.py] An error occurred while setting the port and URL for api: {e}", exc_info=True)


def open_XML(XMLfile, PDFfile, frontend):
    """
    Opens the XML file and converts it to a python dict, and extracts all formulas and figures. Also turns each page of the PDF into an image.

    Paramaters:
    XMLfile: The XML file as stringio object.
    PDFfile: The PDF file as bytes object.
    frontend (bool): Tag stating if frontend is used or not. 

    Returns:
    images: The pages as images from the PDF file.
    figures: The figures from the XML file.
    formulas: The formulas from the XML file.
    """

    logging.info("[classifier.py] Starting function open_XML()")

    # Opening XML file and storing it in variable.
    try:
        global Bs_data
        if (frontend):
            PDFfile = PDFfile.getvalue()
            st.session_state.Bs_data = BeautifulSoup(XMLfile, "xml") # Store XML string data in session state variable which the frontend can access later.
            Bs_data = st.session_state.Bs_data 
        else:
            Bs_data = BeautifulSoup(XMLfile, "xml") # Store XML string data in global variable.
        logging.info(f"[classifier.py] Opened and stored XML and PDF file.")
    except Exception as e:
        logging.error(f"[classifier.py] An error occurred while opening XML and PDF file: {e}", exc_info=True)

    # Finding all figures and formulas in the xml file using their <figure> or <formula> tag:
    figures = Bs_data.find_all('figure')

    formulas = Bs_data.find_all('formula')

    logging.info(f"[classifier.py] Found all figures and formulas in XML file.")

    # Converting the pages in the PDF file to images.
    try:
        images = convert_from_bytes(PDFfile)
        logging.info(f"[classifier.py] Converted the pages in the PDF file to images. Found {len(images)} pages/images.")
    except Exception as e:
        images = []
        logging.error(f"[classifier.py] An error occurred while converting the pages in the PDF file to images: {e}", exc_info=True)

    return images, figures, formulas

def add_to_XML(type, name, newContent, frontend):
    """
    Adds a new element to the XML file. When a non-textual element has been processed it should be placed back into the XML file at the correct location.

    Paramaters:
    type: The type of the element. (figure or formula)
    name: The name of the element. (fig_# or formula_# where # is the number GROBID gave it.)
    newContent: The new content to be added to the XML file as a dict.
    frontend (bool): Tag stating if frontend is used or not. 

    Returns:
    None
    """
    logging.info("[classifier.py] Starting function add_to_XML()")

    ## Find parent tag, and the text content of that:
    try:
        # Find parent tag:
        if (frontend): # Search in session state variable.
            parentTag = st.session_state.Bs_data.find(type, {"xml:id": name})
        else: # Search in global variable.
            parentTag = Bs_data.find(type, {"xml:id": name})
        logging.info(f"[classifier.py] Old parentTag: {parentTag}")
        # If there is no parent tag, then there is nowhere to place the content.
        if (parentTag == None):
            logging.error("[classifier.py] Could not find tag to place element back into...")
            return
        # Try to find all preexisting text in the parent tag, but not counting text in child tags:        
        textWithoutTag = parentTag.find_all(string=True, recursive=False)
        logging.info(f"[classifier.py] Find text in tag: {textWithoutTag}")
    except Exception as e:
        parentTag = ""
        textWithoutTag = []
        logging.error(f"[classifier.py] An error occurred while trying to find parentTag and its content: {e}", exc_info=True)

    # Add the generated content to correct position in new tag
    try:
        if ("formula" in newContent): # Check to see if newContent object has formula key
            newTag = Bs_data.new_tag("latex") # Create new tag
            if (len(textWithoutTag) == 0): # If no preexisting text content in tag:
                parentTag.append(newTag) # Add the new tag to parentTag
            else: # If there already is some text in tag (like the GROBID's attempt at capturing formula):
                for text in textWithoutTag:
                    if (text in parentTag.contents): # Find the text
                        parentTag.contents[parentTag.contents.index(text)].replace_with(newTag) # Replace text with new tag 
                        textWithoutTag = [] # Make sure it doesnt try to replace the newly inserted tag with another later.
                        break
            newTag.string = str(newContent["formula"]) # Set content of new tag to be the value of object key.
            logging.info(f"[classifier.py] Successfully added new formula content to parentTag.")
    except Exception as e:
        logging.error(f"[classifier.py] An error occurred while trying to add new formula content to parentTag: {e}", exc_info=True)
    try:
        if ("NL" in newContent): # Check to see if newContent object has natural language key
            newTag = Bs_data.new_tag("llmgenerated")
            if (len(textWithoutTag) == 0): # If no preexisting text content in tag:
                parentTag.append(newTag)
            else:  # If there already is some text in tag (like the GROBID's attempt at capturing formula):
                for text in textWithoutTag:
                    if (text in parentTag.contents):
                        parentTag.contents[parentTag.contents.index(text)].replace_with(newTag) # Replace text with new tag 
                        textWithoutTag = [] # Make sure it doesnt try to replace the newly inserted tag with another later.
                        break
            newTag.string = newContent["NL"] # Set content of new tag to be the value of object key.        
            logging.info(f"[classifier.py] Successfully added new llmgenerated content to parentTag.")
    except Exception as e:
        logging.error(f"[classifier.py] An error occurred while trying to add new llmgenerated content to parentTag: {e}", exc_info=True)
    try:
        if ("csv" in newContent): # Check to see if newContent object has CSV key
            newTag = Bs_data.new_tag("tabledata")
            if (len(textWithoutTag) == 0): # If no preexisting text content in tag:
                parentTag.append(newTag)
            else: # If there already is some text in tag (like the GROBID's attempt at capturing formula):
                for text in textWithoutTag:
                    if (text in parentTag.contents):
                        parentTag.contents[parentTag.contents.index(text)].replace_with(newTag)
                        textWithoutTag = []
                        break
            newTag.string = str(newContent["csv"])
        logging.info(f"[classifier.py] Successfully added new csv content to parentTag.")
    except Exception as e:
        logging.error(f"[classifier.py] An error occurred while trying to add new csv content to parentTag: {e}", exc_info=True)
    
    logging.info(f"[classifier.py] New parentTag: {parentTag}")

def get_XML(frontend):
   """
   Get function which returns the XML file stored in the variable Bs_data. 

   Paramaters:
   frontend (bool): Tag stating if frontend is used or not. 
   
   Returns:
   Bs_data: The XML file in python dict format.
   """
   logging.info("[classifier.py] Starting function get_XML()")
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
    logging.info("[classifier.py] Starting function saveXMLfile()")
    try:
        with open(pathToXML, "w", encoding="utf-8") as file:
            file.write(str(Bs_data))
        # File is automatically closed after exiting the 'with' block
        logging.info(f"[classifier.py] Successfully saved XML to file.")
        return Bs_data
    except Exception as e:
        logging.error(f"[classifier.py] An error occurred while trying to save XML file: {e}", exc_info=True)

def classify(XMLtype, image, elementNr, pagenr, regex, PDFelementNr, frontend, promptContext=""):
    """
    Classifies a given element as either a formula, chart, figure or other. Based on what the element is classified as 
    it gets redirected to the correct API endpoint for processing. When it gets a response it calls on add_to_XML() to 
    add the generated content back into the XML. If the frontend tag is set, it also sends the API response to the frontend (app.py)
    so that it can be displayed there.

    Paramaters:
    XMLtype: the type of element. (figure or formula)
    image: the image of the element to be sent to the ML model and for processing.
    elementNr: the number which GROBID gave this figure. Will be used when putting processed content back into the figure tag.
    pagenr: the PDF page number of the element.
    regex: the formula string to be matched against regex.
    PDFelementNr: the correct number for the figure, as it is in the PDF. Might not exist because GROBID finds un-numbered figures/formulas sometimes.
    frontend (bool): Tag stating if frontend is used or not. 
    promptContext: A string with the figure description. Can be used to give context to the prompt for the VLM.

    Returns:
    None
    """
    logging.info("[classifier.py] Starting function Classifier()")

    # Get runmode (frontend, code or api)
    envdict = get_envdict()
    if ("runmode" not in envdict): # If key doesnt exist, create it with default value 'api':
        with open("/content/.env", "a") as f:
            f.write("runmode=api\n")
        # File is automatically closed after exiting the 'with' block
    envdict = get_envdict()
    runmode = envdict["runmode"] # Either what the user selected at launch, or default 8000
    if runmode == "code":
        # Code-Launch-processing code:
        import importlib.util
        import sys
        spec = importlib.util.spec_from_file_location("processingmodule", "/content/Sci2XML/app/processing.py")
        processing_launch_code = importlib.util.module_from_spec(spec)
        sys.modules["processingmodule"] = processing_launch_code
        spec.loader.exec_module(processing_launch_code)
        processing_launch_code.print_update(f"Processing {XMLtype} {elementNr}")

        logging.info(f"[classifier.py] Set URL for api to: {apiURL}")

    subtype = "unknown" # The type of element. Will be updated after classification.

    ## API request header:
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    APIresponse = ""

    ## Classifying formulas:
    if (XMLtype == "formula"):
        logging.info(f"[classifier.py] Classifies formula nr:{elementNr}, text: {regex}")
        pattern = r"^(?!\(+$)(?!\)+$).{3,}$"
        ## ^ and $ ensures that the whole string matches.
        ## (?!\(+$) is a negative lookahead that checks that the string doesnt only contain trailing "(".
        ## .{3,} matches any character at least three times, and ensures the string is longer than 2 characters.
        # If the formula meets the criteria for being a formula:
        if (re.match(pattern, regex)):
            logging.info(f"[classifier.py] This formula is indeed a formula.")
            subtype = "formula" # Set type.
            logging.info(f"[classifier.py] Redirecting to formulaParser.")
          
            # Create a bytes object of the image of the element:
            try:
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                logging.info(f"[classifier.py] Successfully converted image of element to bytes object.")
            except Exception as e:
                logging.error(f"[classifier.py] An error occurred while trying create a bytes object of image of element: {e}", exc_info=True)
          
            # Send image of formula to API endpoint where it should be processed by a formula parser:
            try:
                APIresponse = requests.post(apiURL+"parse_formula", files={'image': img_byte_arr})
                # Check that the response is positive:
                if (APIresponse.status_code != 200):
                    logging.error(f"[classifier.py] Something went wrong in the API: {APIresponse.content}")
                    return # Error in API, a proper response is not received.

                APIresponse = APIresponse.json()
                # Set some attributes to the returned response object:
                APIresponse["element_number"] = PDFelementNr
                APIresponse["page_number"] = pagenr
                APIresponse["tag"] = "latex"
                logging.info(f"[classifier.py] Received response from formulaParser in API.")
            except Exception as e:
                logging.error(f"[classifier.py] An error occurred while calling API endpoint for formula parser: {e}", exc_info=True)

            logging.info(f"[classifier.py] Response from formulaParser: {APIresponse}")
        # If the formula does not meets the criteria for being a formula:
        else:
            # Not actually a formula, exiting...
            logging.info(f"[classifier.py] This formula is NOT actually a formula.")
            return 

    ## Classifying figures:
    else:
        ## Send to classifier model first:
        logging.info(f"[classifier.py] Classifies figure nr:{elementNr}.")

        # Create a bytes object of the image of the element:
        try:
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            logging.info(f"[classifier.py] Successfully converted image of element to bytes object.")
        except Exception as e:
            logging.error(f"[classifier.py] An error occurred while trying create a bytes object of image of element: {e}", exc_info=True)

        # Sending image of element to API endpoint for classification:
        try:
            files = {"image": ("image1.png", img_byte_arr)}
            response = requests.post(apiURL+"callClassifier", files=files)
            # Check that the response is positive:
            if (response.status_code != 200):
                logging.error(f"[classifier.py] Something went wrong in the API: {response.content}")
                return # Error in API, a proper response is not received.
            response = response.json()
            figureClass = response["ClassifierResponse"]
            logging.info(f"[classifier.py] Received response from API classifier: {figureClass}. Sending it over to the correct API endpoint.")
        except Exception as e:
            logging.error(f"[classifier.py] An error occurred while calling API endpoint for classification: {e}", exc_info=True)

        # After classification the element is sent to the correct endpoint for further processing.
    
        ## If the figure is of type 'other':
        # That is, 'just_image' elements are likely elements mistaken as figures, 'table' elements are processed separately and not here, 
        # 'text_sentence' elements are mistakes from GROBID where it captures just raw text sentences or paragraphs as figures.
        if (figureClass.lower() in ["just_image", "table", "text_sentence"]):
            logging.info(f"[classifier.py] Element identified as 'other' or unknown. Likely a mistake from GROBID. Exiting...")
            return

        ## If the figure is a 'chart':
        if (figureClass.lower() in ['bar_chart', 'diagram', 'graph', 'pie_chart']):
            logging.info(f"[classifier.py] Element identified as 'chart', subtype: {figureClass.lower()}. Redirecting to chart parser API endpoint...")
            subtype = figureClass.lower() # Set type to what it was classified as.
            ##### APIresponse = API.call("127.0.0.1/chartParser") #####

            # Create a bytes object of the image of the element:
            try:
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                logging.info(f"[classifier.py] Successfully converted image of element to bytes object.")
            except Exception as e:
                logging.error(f"[classifier.py] An error occurred while trying create a bytes object of image of element: {e}", exc_info=True)

            # Send image of figure to API endpoint where it should be processed by a chart parser:
            try:
                APIresponse = requests.post(apiURL+"parse_chart", files={'image': img_byte_arr, 'prompt': promptContext})
                # Check that the response is positive:
                if (APIresponse.status_code != 200):
                    logging.error(f"[classifier.py] Something went wrong in the API: {APIresponse.content}")
                    return # Error in API, a proper response is not received.
                APIresponse = APIresponse.json()
                APIresponse["element_number"] = PDFelementNr
                APIresponse["page_number"] = pagenr
                APIresponse["tag"] = "tabledata"
                logging.info(f"[classifier.py] Received response from chartParser in API.")
            except Exception as e:
                logging.error(f"[classifier.py] An error occurred while calling API endpoint for chart parser: {e}", exc_info=True)

            logging.info(f"[classifier.py] Response from chartParser: {APIresponse}")

        ## If the figure is a 'figure':
        if (figureClass.lower() in ['flow_chart', 'growth_chart']):
            logging.info(f"[classifier.py]  Element identified as 'figure', subtype: {figureClass.lower()}. Redirecting to figure parser API endpoint...")
            subtype = figureClass.lower()

            # Create a bytes object of the image of the element:
            try:
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                logging.info(f"[classifier.py] Successfully converted image of element to bytes object.")
            except Exception as e:
                logging.error(f"[classifier.py] An error occurred while trying create a bytes object of image of element: {e}", exc_info=True)

            # Send image of figure to API endpoint where it should be processed by a figure parser:
            try:
                APIresponse = requests.post(apiURL+"parse_figure", files={'image': img_byte_arr, 'prompt': promptContext})
                # Check that the response is positive:
                if (APIresponse.status_code != 200):
                    logging.error(f"[classifier.py] Something went wrong in the API: {APIresponse.content}")
                    return # Error in API, a proper response is not received.
                APIresponse = APIresponse.json()
                APIresponse["element_number"] = PDFelementNr
                APIresponse["page_number"] = pagenr
                APIresponse["tag"] = "llmgenerated"
                logging.info(f"[classifier.py] Received response from figureParser in API.")
            except Exception as e:
                logging.error(f"[classifier.py] An error occurred while calling API endpoint for figure parser: {e}", exc_info=True)

            logging.info(f"[classifier.py] Response from figureParser: {APIresponse}")

        ## If the classifier thinks that this figure is a formula:
        # Should not happen often. The main handling of formulas happens at the top of this (classify()) function.
        if ("formula" in figureClass.lower()):
            logging.warning(f"[classifier.py] Element identified as 'formula'. Redirecting to formula parser API endpoint...")
            subtype = "formula"

            # Create a bytes object of the image of the element:
            try:
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                logging.info(f"[classifier.py] Successfully converted image of element to bytes object.")
            except Exception as e:
                logging.error(f"[classifier.py] An error occurred while trying create a bytes object of image of element: {e}", exc_info=True)

            # Send image of formula to API endpoint where it should be processed by a formula parser:
            try:
                APIresponse = requests.post(apiURL+"parse_formula", files={'image': img_byte_arr})
                # Check that the response is positive:
                if (APIresponse.status_code != 200):
                    logging.error(f"[classifier.py] Something went wrong in the API: {APIresponse.content}")
                    return # Error in API, a proper response is not received.
                APIresponse = APIresponse.json()
                APIresponse["element_number"] = PDFelementNr
                APIresponse["page_number"] = pagenr
                APIresponse["tag"] = "latex"
                logging.info(f"[classifier.py] Received response from formulaParser in API.")
            except Exception as e:
                logging.error(f"[classifier.py] An error occurred while calling API endpoint for formula parser: {e}", exc_info=True)

            logging.info(f"[classifier.py] Response from formulaParser: {APIresponse}")

    ## If subtype is unknown its better to abort and not add anything back into the XML.
    if (subtype == "unknown"):
      print("Identified as other/unknown. Aborting...")
      logging.info(f"[classifier.py] Element identified as 'other'/unknown. Exiting...")
      return

    # Call on add_to_XML() to add the processed content back into the XML file.
    logging.info(f"[classifier.py] Received response about image nr {elementNr}. Will now paste response back into the XML-file.")
    try:
        if (XMLtype == "figure"):
            add_to_XML(XMLtype, "fig_" + str(elementNr), APIresponse, frontend)
        elif (XMLtype == "formula"):
            add_to_XML(XMLtype, "formula_" + str(elementNr), APIresponse, frontend)
        logging.info(f"[classifier.py] Successfully added content to XML file.")
    except Exception as e:
        logging.error(f"[classifier.py] An error occurred while calling add_to_XML(): {e}", exc_info=True)

    # If the frontend tag is set, the processed content should be returned to the frontend as well:
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
            app.process_classifier_response(APIresponse)
            logging.info(f"[classifier.py] Successfully called frontend function process_classifier_response().")
    except Exception as e:
        logging.error(f"[classifier.py] An error occurred while calling frontend function process_classifier_response(): {e}", exc_info=True)

def process_figures(figures, images, frontend):
    """
    Crops the figures from the PDF file into images, finds correct element number, gets figure description and coordinates and sends them to the classifier (ML model) for classification.

    Paramaters:
    figures: The figures from the XML file.
    images: The PDF pages as images from the PDF file.
    frontend (bool): Tag stating if frontend is used or not. 

    Returns:
    None
    """
    logging.info("[classifier.py] Starting function process_figures()")

    figurnr = 0 # The number which GROBID gave this figure. Will be used when putting processed content back into the figure tag.
    ## Iterate through all figures:
    for figure in figures:

        ## Getting correct figure number:
        correctFigureNr = 0 # The correct number for the figure, as it is in the PDF. Might not exist because GROBID finds un-numbered figures sometimes.
        try:
            # 1. Try to find <label> tag.
            label = figure.find("label")
            if label is not None:
                if (re.sub("\D", "", label.text) != ""):
                    correctFigureNr = int(re.sub("\D", "", label.text))
                    logging.info(f"[classifier.py] Found number in <label> tag.")
                else:
                    # Bad/empty label
                    label = None
            # 2. If the element has no label:
            if label is None:
                #print("NO LABEL")
                logging.info(f"[classifier.py] There is no <label> tag.")
                # 3. If no label tag, look first for (figurnr) in figure.text:
                compare = re.search(r"\(\d+\)$", figure.text)
                if compare:
                    #print("yay, found figurenr in figuretext using regex")
                    logging.info(f"[classifier.py] Found figure number in figure text.")
                    correctFigureNr = int(re.sub("\D", "", compare[0]))
                else:
                    # 4. If no label or figurnr in text, try to use <xml:id> tag:
                    #print("nay, could not find figurenr in label or figuretext, using GROBID's number instead...")
                    logging.info(f"[classifier.py] No figure number in figure text.")
                    if (figure.get("xml:id") != None):
                        correctFigureNr = int(re.sub("\D", "", figure.get("xml:id"))) + 1
                        logging.info(f"[classifier.py] Found figure nr in <xml:id> tag.")
                    else:
                        # 5. If there is no <label> tag, figurenr in text or a <xml:id> tag, use the self-made self-updated figurenr variable.
                        correctFigureNr = figurnr + 1
                        logging.info(f"[classifier.py] Using self-made figure number.")
            logging.info(f"[classifier.py] Successfully found a correct figure number")
        except Exception as e:
            logging.error(f"[classifier.py] An error occurred while trying to find a correct figure number: {e}", exc_info=True)

        logging.info(f"[classifier.py] Correct figure number is now set as: {correctFigureNr}")

        ## Getting figure description (may be used as context for the prompt to figure parser):
        promptContext = ""
        try:
            figureDesc = figure.find("figDesc") # Tries to find any occurance of <figDesc> tag in figure object.
            if figureDesc is not None:
                logging.info(f"[classifier.py] Found figure description {figureDesc}.")
                promptContext = figureDesc.text
            if figureDesc is None:
                logging.info(f"[classifier.py] No figure description found.")
            logging.info(f"[classifier.py] Successfully found figure description.")
        except Exception as e:
            logging.error(f"[classifier.py] An error occurred while trying to find figure description: {e}", exc_info=True)

        ## Getting coordinates:
        coords = ""
        try:
            # If multiple coordinates are found, the last one in the list is used.
            coords = figure.get("coords").split(";")[-1]
        except:
            # If that somehow fails, its likely just one set of coords.
            coords = figure.get("coords")
            
        # The PDF page that this element is on. The page number is the first part of the coords.
        imgside = images[int(coords.split(",")[0])-1] # With '-1' because pdf2image numbers differently than GROBID.
        logging.info(f"[classifier.py] This element is on page nr: {int(coords.split(',')[0])}")

        # When cropping the image of the element from the PDF page we have to use a factor of ca 2.775 to get the correct position. This factor was found thhrough trial and error.
        const = 2.775

        x=float(coords.split(",")[1])
        y=float(coords.split(",")[2])
        x2=float(coords.split(",")[3])
        y2=float(coords.split(",")[4])
        # Use the coords to crop image.
        imgFigur = imgside.crop((x*const,y*const,(x+x2)*const,(y+y2)*const))

        logging.info(f"[classifier.py] Cropped element : {figurnr}. Sending it to classifier...")

        ## Sending to classification:

        classify("figure", imgFigur, figurnr, int(coords.split(",")[0]), None, correctFigureNr, frontend, promptContext)

        figurnr+=1

def process_formulas(formulas, images, mode, frontend):
    """
    Crops the formulas from the PDF file into images, finds correct element number, gets coordinates and sends them to the classifier (ML model) for classification.

    Paramaters:
    formulas: The formulas from the XML file.
    images: The pages as images from the PDF file.
    mode: The mode to be used for classification. (VLM or regex)
    frontend (bool): Tag stating if frontend is used or not. 

    Returns:
    None
    """
    logging.info("[classifier.py] Starting function process_formulas()")

    formulanr = 0 # The number which GROBID gave this formula. Will be used when putting processed content back into the formula tag.
    for formula in formulas:

        ## Getting formula number ##
        correctFigureNr = 0 # The correct number for the formula, as it is in the PDF. Might not exist because GROBID finds un-numbered formulas sometimes.
        try:
            # 1. Try to find <label> tag.
            label = formula.find("label")
            if label is not None:
                if (re.sub("\D", "", label.text) != ""):
                    correctFigureNr = int(re.sub("\D", "", label.text))
                    logging.info(f"[classifier.py] Found number in <label> tag.")
                else:
                    # Bad/empty label
                    label = None
            # 2. If the element has no label:
            if label is None:
                # print("NO LABEL")
                logging.info(f"[classifier.py] There is no <label> tag.")
                # 3. If no label tag, look first for (formulanr) in formula.text
                compare = re.search(r"\(\d+\)$", formula.text)
                if compare:
                    logging.info(f"[classifier.py] Found formula number in formula text.")
                    correctFigureNr = int(re.sub("\D", "", compare[0]))
                else:
                    # 4. If no label or formulanr in text, try to use <xml:id> tag:
                    logging.info(f"[classifier.py] No formula number in formula text.")
                    if (formula.get("xml:id") != None):
                        correctFigureNr = int(re.sub("\D", "", formula.get("xml:id"))) + 1
                        logging.info(f"[classifier.py] Found formula nr in <xml:id> tag.")
                    else:
                        # 5. If there is no <label> tag, formulanr in text or a <xml:id> tag, use the self-made self-updated formulanr variable.
                        correctFigureNr = formulanr + 1
                        logging.info(f"[classifier.py] Using self-made formula number.")
            logging.info(f"[classifier.py] Successfully found a correct figure number")
        except Exception as e:
            logging.error(f"[classifier.py] An error occurred while trying to find a correct figure number: {e}", exc_info=True)

        logging.info(f"[classifier.py] Correct formula number is now set as: {correctFigureNr}")

        ## Getting coords ##
        coords = ""
        try:
            # If multiple coordinates are found, the last one in the list is used.
            coords = formula.get("coords").split(";")[-1]
        except:
            # If that somehow fails, its likely just one set of coords.
            coords = formula.get("coords")

        # The PDF page that this element is on. The page number is the first part of the coords.
        imgside = images[int(coords.split(",")[0])-1] # With '-1' because pdf2image numbers differently than GROBID.
        logging.info(f"[classifier.py] This element is on page nr: {int(coords.split(',')[0])}")

        # When cropping the image of the element from the PDF page we have to use a factor of ca 2.775 to get the correct position. This factor was found thhrough trial and error.
        const = 2.775

        x=float(coords.split(",")[1])
        y=float(coords.split(",")[2])
        x2=float(coords.split(",")[3])
        y2=float(coords.split(",")[4])
        # Use the coords to crop image.
        imgFormula = imgside.crop((x*const,y*const,(x+x2)*const,(y+y2)*const))

        logging.info(f"[classifier.py] Cropped element : {formulanr}. Sending it to classifier...")

        ## Sending to classification:

        if (mode == "VLM"): # If a VLM is used for classifying the formula:
          classify("formula", imgFormula, formulanr, int(coords.split(",")[0]), None, "Answer with only one word (Yes OR No), is this a formula?", correctFigureNr, frontend)
        elif (mode == "regex"): # If regex is used. Preferred.
          classify("formula", imgFormula, formulanr, int(coords.split(",")[0]), formula.text, correctFigureNr, frontend)

        formulanr+=1