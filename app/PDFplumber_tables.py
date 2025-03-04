import os
import re
import logging
import threading
import subprocess
import time
import requests
from tempfile import NamedTemporaryFile
from flask import Flask, request, jsonify, Response
import xml.etree.ElementTree as ET
import pdfplumber

app = Flask(__name__)

# Configure logging to display timestamp and message
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

def extract_tables_from_pdf(pdf_path, max_margin=50):
    """
    Extracts tables from the given PDF file and returns an XML string representing the tables,
    along with the count of tables found.

    Parameters:
        pdf_path (str): Path to the PDF file.
        max_margin (int, optional): Maximum margin for capturing text context near the table. Defaults to 50.

    Returns:
        tuple: A tuple (xml_str, table_count) where xml_str is the XML string of extracted tables,
               and table_count is the number of tables extracted. In case of an error, returns an error message and 0.
    """
    try:
        # Open the PDF file using pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            # Create the root element for the XML structure
            root = ET.Element("pdf_tables")
            table_count = 0

            # Iterate over each page in the PDF
            for page_number, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                # Check if any tables are found on the current page
                if tables:
                    # Iterate over each table found on the page
                    for table_index, table in enumerate(tables, start=1):
                        table_count += 1
                        # Create an XML element for the table with page and table number attributes
                        table_node = ET.SubElement(root, "table", {
                            "page": str(page_number),
                            "table_number": str(table_index)
                        })

                        # Retrieve the bounding box for the table if available
                        table_bbox = page.find_tables()[table_index - 1].bbox if page.find_tables() else None
                        if table_bbox:
                            x0, y0, x1, y1 = table_bbox
                            width = x1 - x0
                            height = y1 - y0
                            coordinates_text = f"{page_number},{x0:.2f},{y0:.2f},{width:.2f},{height:.2f}"
                        else:
                            coordinates_text = f"{page_number},No coordinates found"

                        # Add coordinates information as a child element
                        coordinates_node = ET.SubElement(table_node, "coordinates")
                        coordinates_node.text = coordinates_text

                        # Capture text context from above and below the table
                        words_above = []
                        words_below = []
                        for word in page.extract_words():
                            word_x0, word_y0, word_x1, word_y1 = word['x0'], word['top'], word['x1'], word['bottom']
                            # Check if the word is above the table and within the max margin
                            if word_y1 <= y0 and x0 <= word_x0 <= x1:
                                distance = y0 - word_y1
                                if distance <= max_margin:
                                    words_above.append(word['text'])
                            # Check if the word is below the table and within the max margin
                            if word_y0 >= y1 and x0 <= word_x0 <= x1:
                                distance = word_y0 - y1
                                if distance <= max_margin:
                                    words_below.append(word['text'])
                        # Create context text from the collected words
                        above_text = " ".join(words_above) if words_above else ""
                        below_text = " ".join(words_below) if words_below else ""
                        context = f"Text above table: {above_text}".strip()
                        if below_text:
                            context += f" | Text under table: {below_text}"
                        
                        # Add the context as a child element
                        context_node = ET.SubElement(table_node, "context")
                        context_node.text = context

                        # Add each row of the table as an XML element
                        for row in table:
                            row_node = ET.SubElement(table_node, "row")
                            # Add each cell in the row as an XML element
                            for cell in row:
                                cell_text = str(cell) if cell is not None and cell.strip() else "NAN"
                                cell_node = ET.SubElement(row_node, "cell")
                                cell_node.text = cell_text

            # Convert the XML tree to a string
            xml_str = ET.tostring(root, encoding="utf-8").decode("utf-8")
            # Add a line break before each table element for better readability
            xml_str = xml_str.replace('<table', '\n<table')
        
            return xml_str, table_count
    except Exception as e:
        # In case of an error, return the error message and table count as 0
        return f"Error processing {pdf_path}: {e}", 0

def remove_tables_from_grobid_xml(grobid_file):
    """
    Removes existing table figures from the Grobid XML file and returns the updated XML content
    along with the position of the first removed table.

    Parameters:
        grobid_file (str): Path to the Grobid XML file.

    Returns:
        tuple: A tuple (updated_content, first_table_position) where updated_content is the Grobid XML without table figures,
               and first_table_position is the position (offset) of the first removed table (or None if not found).
    """
    with open(grobid_file, 'r', encoding='utf-8') as file:
        grobid_content = file.read()
    
    # Find all table figure elements in the Grobid XML
    matches = list(re.finditer(r'<figure[^>]*\s+type="table"[^>]*>.*?</figure>', grobid_content, flags=re.DOTALL))
    
    if matches:
        # Get the position of the first table found
        first_table_position = matches[0].start()
    else:
        first_table_position = None
    
    # Remove all table figure elements from the Grobid XML
    updated_content = re.sub(r'<figure[^>]*\s+type="table"[^>]*>.*?</figure>', '', grobid_content, flags=re.DOTALL)
    
    removed_tables = len(matches)
    logging.info(f"{removed_tables} tables removed from {grobid_file}.")
    
    return updated_content, first_table_position

def insert_pdfplumber_content(grobid_xml, pdfplumber_xml, insert_position):
    """
    Inserts the PDFplumber XML content into the Grobid XML content at the specified position.

    Parameters:
        grobid_xml (str): The updated Grobid XML content.
        pdfplumber_xml (str): The XML content extracted from the PDF.
        insert_position (int or None): The position at which to insert the PDFplumber content.
                                       If None, the content is appended at the end.

    Returns:
        str: The final Grobid XML content with the PDFplumber tables inserted.
    """
    # Create a section to mark the beginning and end of the inserted tables
    table_section = (
        "\n<!-- ======== START: Tables from PDFplumber ======== -->\n"
        f"{pdfplumber_xml}\n"
        "<!-- ======== END: Tables from PDFplumber ======== -->\n"
    )

    # Insert the table section at the specified position or append if no position is provided
    if insert_position is not None:
        updated_grobid_xml = grobid_xml[:insert_position] + table_section + grobid_xml[insert_position:]
    else:
        updated_grobid_xml = grobid_xml + "\n" + table_section
    
    return updated_grobid_xml

def remove_empty_lines(xml_content):
    """
    Removes empty lines from the given XML content string.

    Parameters:
        xml_content (str): The XML content as a string.

    Returns:
        str: The XML content without any empty lines.
    """
    return "\n".join([line for line in xml_content.splitlines() if line.strip()])

@app.route("/process", methods=["POST"])
def process_files_api():
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
    # Check if both required files are provided
    if 'pdf' not in request.files or 'grobid_xml' not in request.files:
        return jsonify({"error": "Both PDF and Grobid XML files are required."}), 400
    
    # Retrieve the uploaded files from the request
    pdf_file = request.files['pdf']
    grobid_xml_file = request.files['grobid_xml']
    
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
    grobid_updated, insert_position = remove_tables_from_grobid_xml(grobid_path)
    
    # Extract tables from the PDF and obtain the XML content and table count
    pdfplumber_xml, table_count = extract_tables_from_pdf(pdf_path)
    
    # Insert the PDFplumber XML content into the Grobid XML content
    final_grobid_xml = insert_pdfplumber_content(grobid_updated, pdfplumber_xml, insert_position)
    # Remove any empty lines from the final XML
    final_grobid_xml = remove_empty_lines(final_grobid_xml)
    
    # Remove the temporary files
    os.remove(pdf_path)
    os.remove(grobid_path)
    
    # Return the final Grobid XML as a downloadable file (with content type "application/xml")
    return Response(
        final_grobid_xml,
        mimetype="application/xml",
        headers={"Content-Disposition": "attachment; filename=updated_grobid.xml"}
    )

@app.route("/api", methods=["GET"])
def home():
    """
    Home endpoint that returns a welcome message.

    Parameters:
        None

    Returns:
        JSON: A JSON response with a welcome message.
    """
    return jsonify({"message": "Welcome to the Table Replacement API!"})

def run_flask():
    """
    Runs the Flask application on host 0.0.0.0 and port 5000.

    Parameters:
        None

    Returns:
        None
    """
    app.run(host="0.0.0.0", port=5000)

def get_ip_address():
    """
    Retrieves the external IPv4 address of the host using icanhazip.com.

    Parameters:
        None

    Returns:
        str or None: The external IP address as a string if successful, otherwise None.
    """
    try:
        res = requests.get('https://ipv4.icanhazip.com')
        return res.content.decode('utf8').strip()
    except requests.RequestException as e:
        print(f"Error retrieving IP address: {e}")
        return None

def start_localtunnel():
    """
    Starts a local tunnel using LocalTunnel (npx localtunnel) on port 5000 and prints the public URL.
    
    Parameters:
        None

    Returns:
        None
    """
    print("Starting LocalTunnel...")
    localtunnel = subprocess.Popen(
        ["npx", "localtunnel", "--port", "5000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=True #Remove this if you are not running on local computer e.g. if you are running on colab
    )

    public_url = None
    # Read the stdout lines to find the public URL
    for line in iter(localtunnel.stdout.readline, ""):
        if line:
            if "https://" in line:
                public_url = line.strip()
                print(f"Public URL: {public_url}")
                break
    if not public_url:
        print("Failed to get LocalTunnel URL.")
    else:
        # Retrieve and print the external IP address as a password substitute
        passw = get_ip_address()
        if passw:
            print(f"Flask app is accessible at: {public_url}")
            print(f"Password: {passw}")
        else:
            print("Could not retrieve IP address.")

# Start the Flask server in a separate thread so that it runs in the background
threading.Thread(target=run_flask, daemon=True).start()
time.sleep(3)  # Wait a little to allow the Flask server to start

# Start LocalTunnel to expose the Flask server
start_localtunnel()

print("Server is running. Press CTRL+C to stop.")
try:
    # Keep the main thread alive while the server is running
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Shutting down server...")
