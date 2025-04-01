import requests
import os
import re
import logging
import sys
import time
import pandas as pd
import streamlit as st
import xml.etree.ElementTree as ET
import xml.dom.minidom
import importlib.util
from streamlit_pdf_viewer import pdf_viewer # PDF viewer for displaying PDFs in Streamlit
from annotated_text import annotated_text, annotation # Annotated text library for displaying styled and annotated text

# Configure logging to store logs in a file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s', # Format timestamp
    handlers=[
        logging.FileHandler("app.log"),  # Log to file 'app.log'
        logging.StreamHandler(sys.stdout)  # Also log to console
    ]
)

def latex_validity(latex_str):
    """
    Checks if the LaTeX string has matching \left and \right commands. 
    Checks if the LaTeX string has matching \begin and \end commands. 

    Parameters:
    latex_str (str): The formula in LaTeX format.

    Returns:
    valid (bool): If the formula is on LaTeX format, it returns True. If not, it returns False.
    """

    try:
        # Check for imbalance between \begin and \end
        begin_count = latex_str.count(r"\begin{array}")
        end_count = latex_str.count(r"\end{array}")

        logging.info(f"[app.py] Formula received in latex_validity: {latex_str}")
        logging.info(f"[app.py] \\begin count: {begin_count}")
        logging.info(f"[app.py] \\end count: {end_count}")

        if begin_count != end_count:
            logging.warning(f"[app.py] Imbalanced \\begin and \\end in formula {latex_str}")
            return False

        # Check for imbalance between \left and \right
        left_count = latex_str.count(r"\left")
        right_count = latex_str.count(r"\right")

        logging.info(f"[app.py] \\left count: {left_count}")
        logging.info(f"[app.py] \\right count: {right_count}")

        if left_count != right_count:
            logging.warning(f"[app.py] Imbalanced \\left and \\right in formula {latex_str}")
            return False

    except Exception as e:
        logging.error(f"[app.py] An error occurred while validating formula {latex_str}: {e}", exc_info=True)
        st.error(f"An error occurred while validating a formula.")

    return True

def clean_latex(latex_str):
    """
    Fixes the incorrect usage of \boldmath
    Removes everything after (and including) hskip, eqno and tag.

    Paramaters:
    latex_str (str): The formula on latex format

    Returns:
    latex_str.strip (str): The stripped formula
    """
    try:
        # Remove \boldmath if it's used incorrectly (outside of a valid math environment)
        # Remove \boldmath if it's used outside a valid math block, like an inline formula
        latex_str = re.sub(r'\\boldmath(?!.*\\end\{(?:equation|align|displaymath|[a-z]+)\})', '', latex_str)
        
        # Remove everything after (and including) \hskip
        latex_str = re.sub(r"\\hskip.*", "", latex_str)

        # Remove everything after (and including) \tag
        latex_str = re.sub(r"\\tag.*", "", latex_str)

        # Remove everything after (and including) \eqno
        latex_str = re.sub(r"\\eqno.*", "", latex_str)

        logging.info(f"[app.py] Formula {latex_str} was cleaned successfully!")

    except Exception as e:
        logging.error(f"[app.py] An error occurred while trimming formula {latex_str}: {e}", exc_info=True)
        st.error(f"An error occurred while trimming a formula.")

    return latex_str.strip()  # Trim any extra spaces

def processClassifierResponse(element):
    """
    Processes the response from the classifier and adds it to the correct array.

    Paramaters:
    element (dict): The response from the classifier.

    Returns:
    None
    """
    try:
        if element['element_type'] == 'formula':
            st.session_state.formulas_results_array.append(element) # Append element to the array
            st.subheader(f"Page {element.get('page_number', 'N/A')}: Formula #{element.get('element_number', 'N/A')}") # Display page number and formula number as the header
            if latex_validity(element.get('formula', 'N/A')):
                st.markdown(rf"$$ {clean_latex(element.get('formula', 'N/A'))} $$") # Display the formula itself if on valid LaTeX format
            else:
                st.write('Invalid LaTeX format') # Display 'Invalid LaTeX format' if not on valid LaTeX format  
        
        elif element['element_type'] == "figure":
            st.session_state.figures_results_array.append(element) # Append element to the array
            st.subheader(f"Page {element.get('page_number', 'N/A')}: Figure #{element.get('element_number', 'N/A')}") # Display page number and figure number as the header
            st.text(f"{element.get('NL', 'No description available.')}") # Display the description of the figure

        elif element['element_type'] == "chart":
            st.session_state.charts_results_array.append(element) # Append element to the array
            st.subheader(f"Page {element.get('page_number', 'N/A')}: Chart #{element.get('element_number', 'N/A')}") # Display page number and chart number as the header
            st.text(f"{element.get('NL', 'No description available.')}") # Display the description of the chart

        elif element['element_type'] == "table":
            st.session_state.tables_results_array.append(element) # Append element to the array
            table_data = st.session_state.tables_results_array[-1].get("table_data", []) 
            st.subheader(f"Page {element.get('page_number', 'N/A')}: Table #{element.get('table_number', 'N/A')}") # Display page number and table number as the header
            st.text(f"{element.get('table_context', 'No description available.')}") # Display the context of the table
            if table_data:
                df = pd.DataFrame(table_data) # Convert table data to DataFrame

                st.dataframe(df) # Display the table itself
            else:
                # Inform the user if no table data is found for the current page
                st.write(f"No data found in table on page {element.get('page_number', 'N/A')}.")

        logging.info(f"[app.py] Element was processed successfully!")

    except Exception as e:
        logging.error(f"[app.py] An error occurred while processing the classifier response for element: {e}", exc_info=True)
        st.error(f"An error occurred while processing the classifier response")

def process_classifier(xml_input, pdf_file):
    """
    Processes the input data, including table extraction, figure/formula classification, and parsing, 
    then prettifies the XML output.

    This function performs the following steps:
    1. Calls the table parser to extract table data from the provided XML input.
    2. Processes the extracted data from the table parser.
    3. Uses a classifier to identify figures and formulas in the XML.
    4. Calls the figure and formula parsers to handle the classified figures and formulas.
    5. Processes the parsed figure and formula data.
    6. Prettifies the final XML file to improve human readability.

    Parameters:
    xml_input (str): The XML file content from GROBID.
    pdf_file (file-object): The PDF file uploaded by the user to extract additional data.

    Returns:
    None
    """

    # Check if the session state arrays for the different elements exist or are non-empty.
    # If the arrays exist and are not empty, it means the user has uploaded a second file.
    # In this case, the arrays need to be cleared so that the new results from the second file can be added without conflicts.
    if "formulas_results_array" not in st.session_state or len(st.session_state.formulas_results_array) != 0:
        st.session_state.formulas_results_array = []
    if "figures_results_array" not in st.session_state or len(st.session_state.figures_results_array) != 0:
        st.session_state.figures_results_array = []
    if "charts_results_array" not in st.session_state or len(st.session_state.charts_results_array) != 0:
        st.session_state.charts_results_array = []
    if "tables_results_array" not in st.session_state or len(st.session_state.tables_results_array) != 0:
        st.session_state.tables_results_array = []
    logging.info("[app.py] All session state result arrays for the different elements exist and are empty")

    # Start of the progress bar
    for percent_complete in range(1):
        try:
            # Prepare the files dict to be sent in the request.
            files = {"grobid_xml": ("xmlfile.xml", xml_input, "application/json"), "pdf": ("pdffile.pdf", pdf_file.getvalue())}

            logging.info(f"[app.py] Call the table parser API endpoint")
            # Send to API endpoint for processing of tables
            response = requests.post("http://172.28.0.12:8000/parseTable", files=files)
            response.raise_for_status()  # Raise exception if status is not 200
            logging.info(f'Response from table parser: {response}')

        except requests.exceptions.RequestException as e:
            logging.error(f"[app.py] An error occurred while communication with the table parser: {e}", exc_info=True)
            st.error(f"An error occurred while communication with the table parser.")
        
        try:
            # Define the xml_input and XML namespace
            xml_input = response.text
            namespace = {"tei": "http://www.tei-c.org/ns/1.0"}

            # Parse XML
            root = ET.fromstring(xml_input)

            # Find all <table> elements
            tables = root.findall(".//tei:table", namespace)

            for table in tables:
                page_number = int(table.get("page")) # Retrieve the page number for each table
                table_number = int(table.get("table_number")) # Retrieve the table number for each table

                table_context_element = table.find("tei:context", namespace) # Retrieve the context for each table
                table_context = table_context_element.text.strip() if table_context_element is not None else "Untitled Table" # Strip the context for each table

                # Extract rows inside "this specific table"
                table_rows = table.findall("tei:row", namespace) 

                if table_rows:
                    # Extract headers from the first row of "this specific table"
                    headers = [cell.text.strip() if cell.text else "" for cell in table_rows[0].findall("tei:cell", namespace)]

                    # Ensure headers are not empty before processing rows
                    if headers:
                        table_data = []  # Reset table data for each table

                        # Extract data rows for "this specific table" only
                        for row in table_rows[1:]:  # Skip the header
                            row_data = {}  
                            cells = row.findall("tei:cell", namespace)  # Get cells for the current row
                            for i, cell in enumerate(cells):
                                if i < len(headers):  # Ensure index is within header bounds
                                    row_data[headers[i]] = cell.text.strip() if cell.text else ""  # Strip and add cell text
                            table_data.append(row_data)  # Append the row data to the table

                        # The parsed data will be stored in a results array and displayed to the user
                        processClassifierResponse({
                            "element_type": 'table',
                            "page_number": page_number,
                            "table_number": table_number,
                            "table_context": table_context,
                            "table_data": table_data
                        })
            logging.info(f'[app.py] The XML was parsed successfully!')

        except ET.ParseError as e:
            logging.error(f"[app.py] An error occured while parsing the XML file: {e}", exc_info=True)
            st.error(f"An error occured while parsing the XML file")
        
        # Update progress bar
        st.session_state.progress_bar.progress(percent_complete + 33, text="Classifying elements, and parsing figures & charts... 🔄")

        try:
            # Load classifier module dynamically from specified file location
            spec = importlib.util.spec_from_file_location("classifiermodule", "/content/Sci2XML/app/backend/classifier.py")
            classifier = importlib.util.module_from_spec(spec)
            sys.modules["classifiermodule"] = classifier  # Register the module in sys.modules
            spec.loader.exec_module(classifier)  # Execute the module

            # Classify the figures and formulas by calling 'openXMLfile' from the classifier module
            images, figures, formulas = classifier.openXMLfile(xml_input, pdf_file, frontend=True)
            logging.info(f'[app.py] The non-textual elements were classified successfully!')

        except Exception as e:
            logging.error(f"[app.py] An error occured while classifying the non-textual elements: {e}", exc_info=True)
            st.error(f"An error occured while classifying the non-textual elements.")

        try:
            # Parse the figures by calling 'processFigures' from the classifier module
            classifier.processFigures(figures, images, frontend=True)
            logging.info(f'[app.py] The figures were parsed successfully!')

        except Exception as e:
            logging.error(f"[app.py] An error occured while parsing the figures: {e}", exc_info=True)
            st.error(f"An error occured while parsing the figures.")

        # Update progress bar
        st.session_state.progress_bar.progress(percent_complete + 67, text="Parsing formulas and updating XML file... 🔄")
        
        try:
            # Parse the formulas by calling 'processFormulas' from the classifier module
            classifier.processFormulas(formulas, images, mode="regex", frontend=True)
            logging.info(f'[app.py] The formulas were parsed successfully!')

        except Exception as e:
            logging.error(f"[app.py] An error occured while parsing the formulas: {e}", exc_info=True)
            st.error(f"An error occured while parsing the formulas.")

        try:
            # Extract the version and encoding from the XML declaration using a regex
            version_match = re.search(r'xml version="([^"]+)"', str(st.session_state.Bs_data))
            encoding_match = re.search(r'encoding="([^"]+)"', str(st.session_state.Bs_data))
            version = version_match.group(1) if version_match else '?'  # Default to '?' if no match
            encoding = encoding_match.group(1) if encoding_match else '?'  # Default to '?' if no match

            # Parse the raw XML string into a DOM object
            xml_doc = xml.dom.minidom.parseString(str(st.session_state.Bs_data))

            # Convert the DOM object to a pretty-printed string with a custom indent
            pretty_xml = xml_doc.toprettyxml(indent="	")

            # Remove extra newlines between lines to make the output more compact
            # Split by lines and join back, while skipping any unnecessary empty lines
            pretty_xml_lines = pretty_xml.splitlines()
            cleaned_xml_lines = [line for line in pretty_xml_lines if line.strip()]

            # Join the lines back into a single string
            final_pretty_xml = "\n".join(cleaned_xml_lines)

            #Remove the first line of the XML file
            final_pretty_xml = re.sub(r'<\?xml version="1.0" \?>', '', final_pretty_xml)

            # Add the XML declaration with the correct version and encoding as the first line
            final_xml_with_encoding = f'<?xml version="{version}" encoding="{encoding}"?>{final_pretty_xml}'

            # Store the cleaned, prettified XML back into session state
            st.session_state.interpreted_xml_text = final_xml_with_encoding
            logging.info(f'[app.py] The XML file was prettified successfully!')

        except Exception as e:
            logging.error(f"[app.py] An error occured while prettifying the XML file: {e}", exc_info=True)
            st.error(f"An error occured while pprettifying the XML file.")

        # Update the progress bar
        st.session_state.progress_bar.progress(percent_complete + 100, text="Non-textual elements were interpreted successfully ✅")
    
    # Let the user register the update progress bar before removing it
    time.sleep(4) # Wait 4 seconds
    st.session_state.progress_bar.empty() 

def process_pdf(file, params=None):
    """
    Process a PDF file using the GROBID API and return the response content.

    Parameters:
    file (file-object): The PDF file to process.
    params (dict): Additional parameters for the GROBID request.

    Returns:
    response.text: The XML content returned by the GROBID API as a string, or None if an error occurred.
    """

    # Create a dict with the value as the file to be sent.
    files = {'input': file}

    # Define the URL for the GROBID API endpoint
    grobid_url = "http://172.28.0.12:8070/api/processFulltextDocument"

    try:
        logging.info(f"[app.py] Call GROBID API endpoint")
        response = requests.post(grobid_url, files=files, data=params) # Send request to GROBID
        response.raise_for_status()  # Raise exception if status is not 200
        logging.info(f'[app.py] Response from GROBID: {response}')

        # Check if coordinates are missing in the response
        if 'coords' not in response.text:
            logging.warning("[app.py] No coordinates found in PDF file. Please check GROBID settings.")
            st.warning("No coordinates found in PDF file. Please check GROBID settings.")

        return response.text  # Return XML recevied from GROBID

    except requests.exceptions.RequestException as e:
        logging.error(f"[app.py] An error occured while communicating with GROBID: {e}", exc_info=True)
        st.error(f"An error occured while communicating with GROBID.")
        return None  # Return None on error

def parse_coords_for_figures(xml_content):
    """
    Extract and parse the 'coords' attribute for <figure> and <formula> elements
    from the GROBID XML output while counting the number of occurrences.

    Parameters:
    xml_content (str): The XML content returned by the GROBID API.

    Returns:
    annotations (array): List of annotations with details like page, coordinates, and color.         
    """

    annotations = []

    try:
        # Define the XML namespace
        namespace = {"tei": "http://www.tei-c.org/ns/1.0"}

        # Parse XML
        root = ET.fromstring(xml_content)

        # Find all <figure> and <formula> elements in the XML
        figures = root.findall(".//tei:figure", namespace)
        formulas = root.findall(".//tei:formula", namespace)

        st.session_state.count_figures = len(figures)  # Count figures
        st.session_state.count_formulas = len(formulas)  # Count formulas
        logging.info(f"[app.py] Found {st.session_state.count_figures} figures and {st.session_state.count_formulas} formulas in PDF file.")

        # Process each figure
        for figure in figures:
            coords = figure.attrib.get("coords", None)  # Get 'coords' attribute
            if coords:
                for group in coords.split(';'):  # Loop through each group in 'coords'
                    try:
                        values = list(map(float, group.split(',')))  # Convert to float values
                        if len(values) >= 5:
                            # Extract page and coordinates, add to annotations with red color
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
                        logging.error(f"[app.py] An error occured while parsing figure group '{group}': {e}")
                        st.error(f"An error occured while parsing a figure group.")

        # Process each formula
        for formula in formulas:
            coords = formula.attrib.get("coords", None)  # Get 'coords' attribute
            if coords:
                for group in coords.split(';'):  # Loop through each group in 'coords'
                    try:
                        values = list(map(float, group.split(',')))  # Convert to float values
                        if len(values) >= 5:
                            # Extract page and coordinates, add to annotations with blue color
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
                        logging.error(f"[app.py] An error occured while parsing figure group '{group}': {e}")
                        st.error(f"An error occured while parsing a figure group.")

    except ET.ParseError as e:
        logging.error(f"[app.py] An error occured while parsing GROBID XML: {e}", exc_info=True)
        st.error(f"An error occured while parsing the GROBID XML.")

    return annotations

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
        logging.info(f"[app.py] Variable xml_text successfully set to the current content in text area.")
    except Exception as e:
        logging.error(f"[app.py] An error occurred while setting variable xml_text to the current content in text area: {e}", exc_info=True)
        st.error(f"An error occurred while setting variable xml_text to the current content in text area")

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
        logging.info(f"[app.py] Variable interpreted_xml_text successfully set to the current content in text area.")
    except Exception as e:
        logging.error(f"[app.py] An error occurred while setting variable interpreted_xml_text to the current content in text area: {e}", exc_info=True)
        st.error(f"An error occurred while setting variable interpreted_xml_text to the current content in text area")

def main():
    """
    Extract, process, and display the scientific paper uploaded by the user in PDF format, using GROBID for automatic metadata extraction.

    Parameters:
    None (User uploads a PDF file)
    
    Returns:
    None (Displays the extracted results as a PDF and XML view, allowing the user to edit the XML and download it after processing.
    
    Process:
    1. Initializes the UI with a custom design using st.markdown and applies the provided css.html file.
    2. Accepts a scientific paper in PDF format uploaded by the user.
    3. Sends the PDF to GROBID for metadata extraction and parsing.
    4. Displays the GROBID output both as a rendered PDF and an editable XML text.
    5. Allows the user to modify the XML, if necessary.
    6. Processes the XML by invoking the process_classifier, which classifies and interprets the document's structure.
    7. Displays the interpreted results in views for each element type as well an editable XML text.
    8. Enables the user to refine and download the final XML file.
    """
    st.set_page_config(layout="wide") # Configure the page layout to be wide
    logging.info("[app.py] Streamlit page configuration set successfully.")

    try:
        # Defines the file path to the CSS file
        css_path = os.path.join("app/frontend", "css.html") 

        # Opens the CSS file in read mode and store its content
        with open(css_path, "r") as f: 
            css_content = f.read() # Reads the content of the CSS file
        logging.info(f"[app.py] CSS file '{css_path}' read successfully.")

        # Render the CSS content in the Streamlit app using Markdown with HTML support enabled
        # This allows us to display the raw HTML/CSS content within the Streamlit interface
        st.markdown(f"{css_content}", unsafe_allow_html=True)
        logging.info("[app.py] CSS applied to the Streamlit app successfully.")

    except FileNotFoundError:
        logging.error(f"[app.py] CSS file not found: {css_path}", exc_info=True)
        st.error(f"CSS file not found.")

    except Exception as e:
        logging.error(f"[app.py] An error occurred while applying CSS: {e}", exc_info=True)
        st.error(f"An error occurred while applying CSS.")

    # Title/logo
    st.image("app/images/Sci2XML_logo.png")

    # Declare pdf_ref in session state
    if 'pdf_ref' not in st.session_state:
        st.session_state.pdf_ref = None
        logging.info("[app.py] pdf_ref was missing in session state and has now been initialized.")

    # Access the uploaded ref via a key
    uploaded_pdf = st.file_uploader("Upload PDF", type='pdf', key='pdf', accept_multiple_files=False, label_visibility="hidden")
    
    if uploaded_pdf:
        @st.fragment
        def pdf_upload():
            """
            Sends the uploaded PDF file to GROBID which returns an XML with the parsed data. 
            """
            # Reset session state variables when a new file is uploaded
            if "pdf_ref" in st.session_state and uploaded_pdf != st.session_state.pdf_ref:
                logging.info("[app.py] Uploaded PDF differs from the stored reference. Resetting session state variables")
                st.session_state.show_interpretation_results = False
                st.session_state.xml_text = None
                st.session_state.interpreted_xml_text = None
                st.session_state.results_placeholder = None
                st.session_state.grobid_progress_container = None
                st.session_state.progress_bar = None

            # Backup uploaded file
            st.session_state.pdf_ref = uploaded_pdf

            # Reset pdf_ref when no file is uploaded
            if not st.session_state.pdf:
                logging.warning("[app.py] No PDF file found in session state. Resetting 'pdf_ref' to None.")
                st.session_state.pdf_ref = None

            if st.session_state.pdf_ref:
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

                # Create a container that can be emptied
                st.session_state.grobid_progress_container = st.empty()

                with st.session_state.grobid_progress_container:
                    # Create a status tracker for user transparency
                    with st.status(label="Waiting for GROBID to process the PDF file... 🔄", expanded=False, state="running") as status:
                        try:
                            # Process file as soon as it's uploaded
                            result = process_pdf(st.session_state.pdf_ref, params=params)

                            # If result is not empty, parse the coordinates for figures and store in session state
                            if result:
                                st.session_state.rectangles = parse_coords_for_figures(result)
                            else:
                                # If no result, reset rectangles in session state and clear the result
                                st.session_state.rectangles = []
                                result = ""
                            status.update(label="The PDF file was processed successfully by GROBID ✅", state="complete", expanded=False)
                            logging.info("[app.py] The PDF file was processed by GROBID successfully!")

                        except Exception as e:
                            logging.error(f"[app.py] An error occurred when receiving the GROBID result: {e}", exc_info=True)
                            st.error(f"An error occurred when receiving the GROBID result.")

                # Initialize the xml_text and show_grobid_results in session_state if not already set
                if "xml_text" not in st.session_state or st.session_state.xml_text is None:
                    st.session_state.xml_text = result  # Initial XML content from GROBID

                if "show_grobid_results" not in st.session_state:
                    st.session_state.show_grobid_results = True  # Set session state flag

        pdf_upload()

        if st.session_state.show_grobid_results:
        # Layout container to maintain column structure
            with st.container():
                # Achieve small space between col1 & col3 by initializing col2 without using it
                col1, col2, col3 = st.columns([0.45, 0.1, 0.45]) # col1 & col3 are 45% each while col1 is 10%

                # Display GROBID results in col1
                with col1:
                    @st.fragment
                    def grobid_results_view():
                        """
                        Render the GROBID results in either PDF View with annotations or raw XML View.
                        """
                        st.header("GROBID Results", divider="gray")

                        if 'grobid_results_view_option' not in st.session_state:
                            st.session_state.grobid_results_view_option = "PDF 📄" # Deault to PDF View

                        # Create radio buttons to switch between views
                        st.session_state.grobid_results_view_option = st.radio("Select View", ["PDF 📄", "XML 📝"], horizontal=True, key='view_toggle', label_visibility="collapsed")

                        # Display PDF view with annotations
                        if st.session_state.grobid_results_view_option == "PDF 📄":
                            # Show the PDF with annotations (rectangles) and rendered text
                            try:
                                logging.info("[app.py] Calling the PDF Viewer")
                                pdf_viewer(input=st.session_state.pdf_ref.getvalue(), height=775, annotations=st.session_state.rectangles, render_text=True, annotation_outline_size=2)
                                logging.info("[app.py] The PDF file was processed by PDF Viewer successfully!")

                            except Exception as e:
                                logging.error(f"[app.py] An error occurred when calling the PDF Viewer: {e}", exc_info=True)
                                st.error(f"An error occurred when calling the PDF Viewer.")

                            try:
                                # Display annotation text based on the presence of formulas and figures
                                if st.session_state.count_formulas > 0 and st.session_state.count_figures > 0:
                                    # Annotate both formulas and figures
                                    annotated_text(
                                        annotation("Formulas", "", background="#0000FF", color="#FFFFFF"), " ",
                                        annotation("Figures", "", background="#CC0000", color="#FFFFFF")
                                    )

                                elif st.session_state.count_formulas > 0:
                                    # Annotate only formulas
                                    annotated_text(
                                        annotation("Formulas", "", background="#0000FF", color="#FFFFFF")
                                    )

                                elif st.session_state.count_figures > 0:
                                    # Annotate only figures
                                    annotated_text(
                                        annotation("Figures", "", background="#CC0000", color="#")
                                    )
                                logging.info("[app.py] Annoted Text was displayed successfully!")

                            except Exception as e:
                                logging.error(f"[app.py] An error occurred when calling Annoted Text: {e}", exc_info=True)
                                st.error(f"An error occurred when calling Annoted Text.")

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

                    # Empty the status tracker when both views are created
                    st.session_state.grobid_progress_container.empty()

                    @st.fragment
                    def classify2():
                        """
                        Sends the PDF file and XML file to the classifier when "Process file"-button is clicked.
                        """
                        if st.button("Process file"):
                            # Display Interpretated results in col3
                            with col3:
                                if 'results_placeholder' not in st.session_state or st.session_state.results_placeholder == None:
                                    # Create header, as well as progress bar and container in session state first time a PDF is processed
                                    st.header("Interpretation Results", divider="gray") 
                                    st.session_state.progress_bar = st.progress(0, text="Parsing tables... 🔄") # Progress bar for user transparency
                                    st.session_state.results_placeholder = st.empty() # Container that can be emptied if the user processes another file
                                else:
                                    # If it not the first time a PDF is processed, do not create header, progress bar and container as they already exist
                                    st.session_state.results_placeholder.empty() # Empty earlier results

                                # Create container with the different views for Interpreted Results
                                with st.session_state.results_placeholder.container():
                                    # Initialize the interpretation_results_view_option in session_state if not already set
                                    if 'interpretation_results_view_option' not in st.session_state:
                                        st.session_state.interpretation_results_view_option = "XML 📝" # Set default to XML

                                # Empty the results when both views are created
                                st.session_state.results_placeholder.empty()

                                # Create a container that can be emptied after displaying the results as they are processed by the parsers
                                container_placeholder = st.empty()

                                with container_placeholder.container(height=775, border=True):
                                    try:
                                        # Process the PDF file and XML file by calling the classifier and parsers
                                        process_classifier(st.session_state.xml_text, st.session_state.pdf_ref)  # Use PDF file and updated XML file from session state
                                        logging.info("[app.py] The PDF file and XML file were processed by the classifier and parsers successfully!")

                                    except Exception as e:
                                        logging.error(f"[app.py] An error occurred when processing the PDF file and XML file in the classifier: {e}", exc_info=True)
                                        st.error(f"An error occurred when processing the PDF file and XML file in the classifier.")

                                # Empty the results placeholder when all the elements have been parsed
                                container_placeholder.empty()

                                with col3:
                                    with st.session_state.results_placeholder.container():
                                        @st.fragment
                                        def interpretation_results_view():
                                            """
                                            Render different interpretation results based on user selection.
                                            """

                                            # Create radio buttons to switch between views
                                            st.session_state.interpretation_results_view_option = st.radio("Select Non-Textual Element", ["XML 📝", "Formulas 🔢", "Figures 🖼️", "Charts 📊", "Tables 📋"], horizontal=True, key='interpretation_toggle', label_visibility="collapsed")

                                            # If 'XML' is chosen, display XML result
                                            if st.session_state.interpretation_results_view_option == "XML 📝":
                                                st.text_area(
                                                    "Edit Interpreted XML File",
                                                    value=st.session_state.interpreted_xml_text,  # Initial content from session state
                                                    height=775,
                                                    key="interpreted_xml_editor",  # Key for the text area
                                                    on_change=update_interpreted_xml,  # Update xml_text when changes are made
                                                    label_visibility="collapsed" # Hide the label properly
                                                )

                                            # If 'Formulas' is chosen, display XML result
                                            elif st.session_state.interpretation_results_view_option == "Formulas 🔢":
                                                with st.container(height=775, border=True):
                                                    if len(st.session_state.formulas_results_array) > 0:
                                                        for formula in st.session_state.formulas_results_array:  # Use session state variable
                                                            st.subheader(f"Page {formula.get('page_number', 'N/A')}: Formula #{formula.get('element_number', 'N/A')}") # Display page number and formula number as the header
                                                            if latex_validity(formula.get('formula', 'N/A')):
                                                                st.markdown(rf"$$ {clean_latex(formula.get('formula', 'N/A'))} $$") # Display the formula itself if on valid LaTeX format
                                                            else:
                                                                st.write('Invalid LaTeX format') # Display 'Invalid LaTeX format' if not on valid LaTeX format                                                      
                                                    else:
                                                        st.warning("No formulas detected in PDF file.")

                                            # If 'Figures' is chosen, display XML result
                                            elif st.session_state.interpretation_results_view_option == "Figures 🖼️":
                                                with st.container(height=775, border=True):
                                                    if len(st.session_state.figures_results_array) > 0:
                                                        for figure in st.session_state.figures_results_array:  # Use session state variable
                                                            st.subheader(f"Page {figure.get('page_number', 'N/A')}: Figure #{figure.get('element_number', 'N/A')}") # Display page number and figure number as the header
                                                            st.text(f"{figure.get('NL', 'No description available.')}") # Display the description of the figure
                                                    else:
                                                        st.warning("No figures detected in PDF file.")

                                            # If 'Charts' is chosen, display XML result
                                            elif st.session_state.interpretation_results_view_option == "Charts 📊":
                                                with st.container(height=775, border=True):
                                                    if len(st.session_state.charts_results_array) > 0:
                                                        for chart in st.session_state.charts_results_array:  # Use session state variable
                                                            st.subheader(f"Page {chart.get('page_number', 'N/A')}: Chart #{chart.get('element_number', 'N/A')}") # Display page number and chart number as the header
                                                            st.text(f"{chart.get('NL', 'No description available.')}") # Display the description of the chart
                                                    else:
                                                        st.warning("No charts detected in PDF file.")

                                            # If 'Tables' is chosen, display XML result
                                            elif st.session_state.interpretation_results_view_option == "Tables 📋":
                                                with st.container(height=775, border=True):
                                                    if len(st.session_state.tables_results_array) > 0:
                                                        for table in st.session_state.tables_results_array:
                                                            table_data = table.get("table_data", [])
                                                            st.subheader(f"Page {table.get('page_number', 'N/A')}: Table #{table.get('table_number', 'N/A')}") # Display page number and table number as the header
                                                            st.text(f"{table.get('table_context', 'No description available.')}") # Display the context of the table
                                                            if table_data:
                                                                # Convert table data to DataFrame
                                                                df = pd.DataFrame(table_data)

                                                                st.dataframe(df) # Display the table itself
                                                            else:
                                                                st.write(f"No data found in table on page {table.get('page_number', 'N/A')}.")
                                                    else:
                                                        st.warning("No tables detected in PDF file.")

                                            # Download button of the XML file
                                            st.download_button(
                                                label="Download XML",
                                                data=st.session_state.interpreted_xml_text.encode("utf-8"), # Convert text to bytes
                                                file_name="interpreted_results.xml", # File name
                                                mime="application/xml"
                                            )

                                        interpretation_results_view()

                    classify2()
    else:
        # Prompt user to upload a PDF file if not PDF file is uploaded
        st.write("Upload a PDF file to analyze it in GROBID")

if __name__ == '__main__':
    main()