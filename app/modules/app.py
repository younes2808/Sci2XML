print("Starting Streamlit app...")

import streamlit as st
import requests
import os
import pandas as pd
import re
import xml.etree.ElementTree as ET
import xml.dom.minidom
import streamlit as st
import logging
import sys
import time
import importlib.util
from streamlit_pdf_viewer import pdf_viewer
from annotated_text import annotated_text, annotation

from pdf2image import convert_from_path, convert_from_bytes
from pdf2image.exceptions import (
    PDFInfoNotInstalledError,
    PDFPageCountError,
    PDFSyntaxError
)

def clean_latex(latex_str):
    """
    Removes everything after (and including) \hskip or \tag.
    """
    # Remove everything after (and including) \hskip
    latex_str = re.sub(r"\\hskip.*", "", latex_str)

    # Remove everything after (and including) \tag
    latex_str = re.sub(r"\\tag.*", "", latex_str)

    # Remove everything after (and including) \eqno
    latex_str = re.sub(r"\\eqno.*", "", latex_str)

    return latex_str.strip()  # Trim any extra spaces

def processClassifierResponse(element):
    """
    Processes the response from the classifier and adds it to the correct array.

    Paramaters:
    APIresponse: The response from the classifier as a object/dict. Ex: "{'NL': 'some NL', 'element_type': 'figure', 'preferred': 'some NL', 'element_number': 1, 'page_number': 1}"

    Returns:
    None
    """
    if element['element_type'] == 'formula':
        st.session_state.formulas_results_array.append(element)
        st.subheader(f"Page {element.get('page_number', 'N/A')}: Formula #{element.get('element_number', 'N/A')}")
        st.markdown(rf"$$ {clean_latex(element.get('formula', 'N/A'))} $$")

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
        table_data = st.session_state.tables_results_array[-1].get("table_data", [])
        st.subheader(f"Page {element.get('page_number', 'N/A')}: Table #{element.get('table_number', 'N/A')}")
        st.text(f"{element.get('table_context', 'No description available.')}")
        if table_data:
            # Convert table data to DataFrame
            df = pd.DataFrame(table_data)

            # Display table
            st.dataframe(df)
        else:
            st.write(f"No data found in table on page {element.get('page_number', 'N/A')}.")

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
        css_path = os.path.join("app/modules", "css.html")
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

        for percent_complete in range(1):
            ## Table Parser ##
            ### Run the xml and pdf through the tableparser before processing further. Could also be done after the processing of the other elements instead.
            logging.info("Initiating table parser")
            # Ready the files
            files = {"grobid_xml": ("xmlfile.xml", xml_input, "application/json"), "pdf": ("pdffile.pdf", pdf_file.getvalue())}

            # Send to API endpoint for processing of tables
            response = requests.post("http://172.28.0.12:8000/parseTable", files=files)

            logging.info(f'response: {response}')
            logging.info(f'response content: {response.content}')
            logging.info(f'response text: {response.text}')
            xml_input = response.text

            # Define the XML namespace
            namespace = {"tei": "http://www.tei-c.org/ns/1.0"}

            # Parse XML
            root = ET.fromstring(xml_input)

            # Find all <table> elements
            tables = root.findall(".//tei:table", namespace)

            for table in tables:
                page_number = int(table.get("page"))
                table_number = int(table.get("table_number"))

                table_context_element = table.find("tei:context", namespace)
                table_context = table_context_element.text.strip() if table_context_element is not None else "Untitled Table"

                # Extract rows *inside this specific table*
                table_rows = table.findall("tei:row", namespace)

                if table_rows:
                    # Extract headers from the first row of *this table*
                    headers = [cell.text.strip() if cell.text else "" for cell in table_rows[0].findall("tei:cell", namespace)]

                    # Ensure headers are not empty before processing rows
                    if headers:
                        table_data = []  # Reset table data for each table

                        # Extract data rows for *this table only*
                        for row in table_rows[1:]:  # Skip header row
                            row_data = {}
                            cells = row.findall("tei:cell", namespace)  # Get only this row's cells
                            for i, cell in enumerate(cells):
                                if i < len(headers):  # Ensure index is within bounds
                                    row_data[headers[i]] = cell.text.strip() if cell.text else ""
                            table_data.append(row_data)

                        # Store table details (ensuring only this table's rows are processed)
                        processClassifierResponse({
                            "element_type": 'table',
                            "page_number": page_number,
                            "table_number": table_number,
                            "table_context": table_context,
                            "table_data": table_data
                        })
            
            st.session_state.progress_bar.progress(percent_complete + 33, text="Classifying and parsing figures & charts... 🔄")

            ## Process XML ##
            spec = importlib.util.spec_from_file_location("classifiermodule", "/content/Sci2XML/app/modules/classifier.py")
            classifier = importlib.util.module_from_spec(spec)
            sys.modules["classifiermodule"] = classifier
            spec.loader.exec_module(classifier)
            images, figures, formulas = classifier.openXMLfile(xml_input, pdf_file, frontend=True)

            classifier.processFigures(figures, images, frontend=True)

            st.session_state.progress_bar.progress(percent_complete + 67, text="Parsing formulas and generating XML file... 🔄")
            classifier.processFormulas(formulas, images, mode="regex", frontend=True)

            # Assuming st.session_state.interpreted_xml_text contains your raw XML string
            raw_xml = str(st.session_state.Bs_data)

            # Extract the version and encoding from the XML declaration using a regex
            version_match = re.search(r'xml version="([^"]+)"', raw_xml)
            version = version_match.group(1) if version_match else '?'  # Default to ?
            encoding_match = re.search(r'encoding="([^"]+)"', raw_xml)
            encoding = encoding_match.group(1) if encoding_match else '?'  # Default to ?

            # Parse the raw XML string into a DOM object
            xml_doc = xml.dom.minidom.parseString(raw_xml)

            # Convert the DOM object to a pretty-printed string with a custom indent
            pretty_xml = xml_doc.toprettyxml(indent="	")

            # Remove extra newlines between lines to make the output more compact
            # Split by lines and join back, while skipping any unnecessary empty lines
            pretty_xml_lines = pretty_xml.splitlines()
            cleaned_xml_lines = [line for line in pretty_xml_lines if line.strip()]

            # Join the lines back into a single string
            final_pretty_xml = "\n".join(cleaned_xml_lines)

            final_pretty_xml = re.sub(r'<\?xml version="1.0" \?>', '', final_pretty_xml)

            # Add the XML declaration with the correct encoding at the beginning
            final_xml_with_encoding = f'<?xml version="{version}" encoding="{encoding}"?>{final_pretty_xml}'

            # Store the cleaned, prettified XML back into session state
            st.session_state.interpreted_xml_text = final_xml_with_encoding

            logging.info("Generated XML:\n" + st.session_state.interpreted_xml_text)

            st.session_state.progress_bar.progress(percent_complete + 100, text="Non-Textual Elements were interpreted successfully ✅")
        time.sleep(4)
        st.session_state.progress_bar.empty()

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
    st.image("app/images/Sci2XML_logo.png")

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
                st.session_state.grobid_progress_container = None
                st.session_state.progress_bar = None

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

                st.session_state.grobid_progress_container = st.empty()
                with st.session_state.grobid_progress_container:
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
                        status.update(label="The file was processed successfully by GROBID ✅", state="complete", expanded=False)

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
                col1, col2, col3 = st.columns([0.45, 0.1, 0.45])

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
                            pdf_viewer(input=st.session_state.pdf_ref.getvalue(), height=775, annotations=st.session_state.rectangles, render_text=True, annotation_outline_size=2)
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
                                height=775,
                                key="xml_editor",  # Key for the text area
                                on_change=update_xml,  # Update xml_text when changes are made
                                label_visibility="collapsed" # Hide the label properly
                            )

                    grobid_results_view()

                    time.sleep(4)
                    st.session_state.grobid_progress_container.empty()

                    @st.fragment
                    def classify2():
                        if st.button("Process file"):
                            with col3:
                                if 'results_placeholder' not in st.session_state or st.session_state.results_placeholder == None:
                                    st.header("Interpretation Results", divider="gray")  # Always stays aligned with col1
                                    st.session_state.progress_bar = st.progress(0, text="Parsing tables... 🔄")
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

                                with container_placeholder.container(height=775, border=True):
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
                                                    height=775,
                                                    key="interpreted_xml_editor",  # Key for the text area
                                                    on_change=update_interpreted_xml,  # Update xml_text when changes are made
                                                    label_visibility="collapsed" # Hide the label properly
                                                )

                                            elif st.session_state.interpretation_results_view_option == "Formulas 🔢":
                                                with st.container(height=775, border=True):
                                                    if len(st.session_state.formulas_results_array) > 0:
                                                        for formula in st.session_state.formulas_results_array:  # Use session state variable
                                                            st.subheader(f"Page {formula.get('page_number', 'N/A')}: Formula #{formula.get('element_number', 'N/A')}")
                                                            st.markdown(rf"$$ {clean_latex(formula.get('formula', 'N/A'))} $$")
                                                    else:
                                                        st.warning("No formulas detected in PDF file.")

                                            elif st.session_state.interpretation_results_view_option == "Figures 🖼️":
                                                with st.container(height=775, border=True):
                                                    if len(st.session_state.figures_results_array) > 0:
                                                        for figure in st.session_state.figures_results_array:  # Use session state variable
                                                            st.subheader(f"Page {figure.get('page_number', 'N/A')}: Figure #{figure.get('element_number', 'N/A')}")
                                                            st.text(f"{figure.get('NL', 'No description available.')}")
                                                    else:
                                                        st.warning("No figures detected in PDF file.")

                                            elif st.session_state.interpretation_results_view_option == "Charts 📊":
                                                with st.container(height=775, border=True):
                                                    if len(st.session_state.charts_results_array) > 0:
                                                        for chart in st.session_state.charts_results_array:  # Use session state variable
                                                            st.subheader(f"Page {chart.get('page_number', 'N/A')}: Chart #{chart.get('element_number', 'N/A')}")
                                                            st.text(f"{chart.get('NL', 'No description available.')}")
                                                    else:
                                                        st.warning("No charts detected in PDF file.")

                                            elif st.session_state.interpretation_results_view_option == "Tables 📋":
                                                with st.container(height=775, border=True):
                                                    if len(st.session_state.tables_results_array) > 0:
                                                        for table in st.session_state.tables_results_array:  # Use session state variable
                                                            table_data = table.get("table_data", [])
                                                            st.subheader(f"Page {table.get('page_number', 'N/A')}: Table #{table.get('table_number', 'N/A')}")
                                                            st.text(f"{table.get('table_context', 'No description available.')}")
                                                            if table_data:
                                                                # Convert table data to DataFrame
                                                                df = pd.DataFrame(table_data)

                                                                # Display table
                                                                st.dataframe(df)
                                                            else:
                                                                st.write(f"No data found in table on page {table.get('page_number', 'N/A')}.")
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