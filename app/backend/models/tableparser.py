import xml.etree.ElementTree as ET
import pdfplumber
import re
import logging

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
                            "table_number": str(table_count)
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
    Removes existing table figures from the GROBID XML file and returns the updated XML content
    along with the position of the first removed table.

    Parameters:
        grobid_file (str): Path to the GROBID XML file.

    Returns:
        tuple: A tuple (updated_content, first_table_position) where updated_content is the GROBID XML without table figures,
               and first_table_position is the position (offset) of the first removed table (or None if not found).
    """
    with open(grobid_file, 'r', encoding='utf-8') as file:
        grobid_content = file.read()
    
    # Find all table figure elements in the GROBID XML
    matches = list(re.finditer(r'<figure[^>]*\s+type="table"[^>]*>.*?</figure>', grobid_content, flags=re.DOTALL))
    
    if matches:
        # Get the position of the first table found
        first_table_position = matches[0].start()
    else:
        first_table_position = None
    
    # Remove all table figure elements from the GROBID XML
    updated_content = re.sub(r'<figure[^>]*\s+type="table"[^>]*>.*?</figure>', '', grobid_content, flags=re.DOTALL)
    
    removed_tables = len(matches)
    logging.info(f"[tableparser] {removed_tables} tables removed from {grobid_file}.")
    
    return updated_content, first_table_position

def insert_pdfplumber_content(grobid_xml, pdfplumber_xml, insert_position):
    """
    Inserts the PDFplumber XML content into the GROBID XML content at the specified position.

    Parameters:
        grobid_xml (str): The updated GROBID XML content.
        pdfplumber_xml (str): The XML content extracted from the PDF.
        insert_position (int or None): The position at which to insert the PDFplumber content.
                                       If None, the content is appended at the end.

    Returns:
        str: The final GROBID XML content with the PDFplumber tables inserted.
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
        # No <table> tag found, adding it to the end of document:
        TEImatches = list(re.finditer(r'</TEI>', grobid_xml, flags=re.DOTALL))
        if TEImatches:
            # Get the position of the end TEI tag
            first_table_position = TEImatches[0].start()
            updated_grobid_xml = grobid_xml[:first_table_position] + table_section + grobid_xml[first_table_position:]
        else:
            first_table_position = None
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