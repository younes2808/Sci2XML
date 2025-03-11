import requests, json
from PIL import Image
import io
from io import StringIO
import streamlit as st

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
import re
from app import processClassifierResponse

apiURL = "http://172.28.0.12:8000/"

def openXMLfile(XMLfile, PDFfile, frontend):
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
    if (frontend):
      st.session_state.Bs_data = BeautifulSoup(XMLfile, "xml")
      #Bs_data = BeautifulSoup(data, "xml")
      Bs_data = st.session_state.Bs_data
    else:
      Bs_data = BeautifulSoup(XMLfile, "xml")

    figures = Bs_data.find_all('figure')

    print("Figures:")
    print(figures)

    formulas = Bs_data.find_all('formula')

    print("Formulas:")
    print(formulas)

    #images = convert_from_path(pathToPDF, poppler_path='C:\\Program Files\\Release-24.08.0-0\\poppler-24.08.0\\Library\\bin')
    #images = convert_from_path(pathToPDF)
    images = convert_from_bytes(PDFfile)

    for i in range(0, len(images)):
        print("--- Image nr ", i+1)

    return images, figures, formulas

def addToXMLfile(type, name, newContent, frontend):
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
    if (frontend):
      parentTag = st.session_state.Bs_data.find(type, {"xml:id": name})
    else:
      parentTag = Bs_data.find(type, {"xml:id": name})
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

def classify(XMLtype, image, elementNr, pagenr, regex, PDFelementNr, frontend):
    """
    Classifies a given element as either a formula, table, chart or figure.

    Paramaters:
    XMLtype: the type of element. (figure or formula)
    image: the image to be sent to the VLM model.
    elementNr: the number which Grobid gave this figure. Will be used when putting processed content back into the figure tag.
    pagenr: the page number of the element.
    regex: the formula string to be matched against regex.
    PDFelementNr: the correct number for the figure, as it is in the PDF. Might not exist because Grobid finds un-numbered figures sometimes.

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
          subtype = "formula"
          print("Redirecting to formulaParser")
          ##### APIresponse = API.call("127.0.0.1/formulaParser") #####

          img_byte_arr = io.BytesIO()
          image.save(img_byte_arr, format='PNG')
          img_byte_arr = img_byte_arr.getvalue()

          APIresponse = requests.post(apiURL+"parseFormula", files={'image': img_byte_arr})
          APIresponse = APIresponse.json()
          APIresponse["element_number"] = PDFelementNr
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
          ##### APIresponse = API.call("127.0.0.1/chartParser") #####
          img_byte_arr = io.BytesIO()
          image.save(img_byte_arr, format='PNG')
          img_byte_arr = img_byte_arr.getvalue()

          APIresponse = requests.post(apiURL+"parseChart", files={'image': img_byte_arr})
          APIresponse = APIresponse.json()
          APIresponse["element_number"] = PDFelementNr
          APIresponse["page_number"] = pagenr

          print("Response from chartParser: --> ", APIresponse["preferred"])

      ## For figures:
      if (figureClass.lower() in ['flow_chart', 'growth_chart']):
          print("Redirecting to figureParser. Image identified as ", figureClass.lower())
          subtype = figureClass.lower()
          ##### APIresponse = API.call("127.0.0.1/figureParser") #####
          img_byte_arr = io.BytesIO()
          image.save(img_byte_arr, format='PNG')
          img_byte_arr = img_byte_arr.getvalue()

          APIresponse = requests.post(apiURL+"parseFigure", files={'image': img_byte_arr})
          APIresponse = APIresponse.json()
          APIresponse["element_number"] = PDFelementNr
          APIresponse["page_number"] = pagenr

          print("Response from figureParser: --> ", APIresponse["preferred"])

      ## For formulas
      if ("formula" in figureClass.lower()):
        print("Redirecting to formulaParser")
        subtype = "formula"
        ##### APIresponse = API.call("127.0.0.1/formulaParser") #####
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()

        APIresponse = requests.post(apiURL+"parseFormula", files={'image': img_byte_arr})
        APIresponse = APIresponse.json()
        APIresponse["element_number"] = PDFelementNr
        APIresponse["page_number"] = pagenr

        print("Response from formulaParser: --> ", APIresponse["preferred"])

    ## If subtype is unknown its better to abort and not add anything back into the XML.
    if (subtype == "unknown"):
      print("Identified as other/unknown. Aborting...")
      return

    print("Received response about image nr ", elementNr, ". Will now paste response back into the XML-file.")
    if (XMLtype == "figure"):
      addToXMLfile(XMLtype, "fig_" + str(elementNr), APIresponse, frontend=True)
    elif (XMLtype == "formula"):
      addToXMLfile(XMLtype, "formula_" + str(elementNr), APIresponse, frontend=True)

    ## This writes directly to screen. Is used for testing, should only be added to array instead.
    #st.write(f"Received response about {XMLtype}. It was a {subtype}. APIresponse: {APIresponse}")

    if (frontend):
      ## Adds to arrays:
      processClassifierResponse(APIresponse)



def processFigures(figures, images, frontend):
    """
    Crops the figures from the PDF file into images and sends them to the classifier (ML model) for classification.

    Paramaters:
    figures: The figures from the XML file.
    images: The pages as images from the PDF file.

    Returns:
    None
    """
    print("\n-------- Cropping Figures --------")
    figurnr = 0 # The number which Grobid gave this figure. Will be used when putting processed content back into the figure tag.
    for figure in figures:

        ## Getting figure number ##
        correctFigureNr = 0 # The correct number for the figure, as it is in the PDF. Might not exist because Grobid finds un-numbered figures sometimes.
        label = figure.find("label")
        if label is not None:
            if (re.sub("\D", "", label.text) != ""):
                correctFigureNr = int(re.sub("\D", "", label.text))
            else:
                # Bad/empty label
                label = None
        if label is None:
            print("NO LABEL")
            # If no label tag, look for (figurnr) in figure.text
            compare = re.search(r"\(\d+\)$", figure.text)
            if compare:
                print("yay, found figurenr in figuretext using regex")
                correctFigureNr = int(re.sub("\D", "", compare[0]))
            else:
                print("nay, could not find figurenr in label or figuretext, using Grobid's number instead...")
                # If no match, just use xml:id i guess
                correctFigureNr = int(re.sub("\D", "", figure.get("xml:id"))) + 1
        print("----------> FOUND FIGURE NR: ", correctFigureNr)

        ## Getting coords ##
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

        ## SENDING TO CLASSIFICATION...

        classify("figure", imgFigur, figurnr, int(coords.split(",")[0]), None, correctFigureNr, frontend=True)

        figurnr+=1
        print("----------")

def processFormulas(formulas, images, mode, frontend):
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
          classify("formula", imgFormula, formulanr, int(coords.split(",")[0]), formula.text, correctFigureNr, frontend=True)

        formulanr+=1
        print("----------")
