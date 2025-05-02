import pdfplumber
import os
import xml.etree.ElementTree as ET
import time
import re

def extract_tables_from_pdf(pdf_path, output_dir, max_margin=50):
    """
    Extracts tables from a single PDF and writes them to an XML file.

    Args:
        pdf_path (str): Path to the PDF file.
        output_dir (str): Directory where the XML output will be saved.
        max_margin (int): Maximum vertical margin (in points) to capture context text above and below tables.

    Returns:
        int: Number of tables extracted.
    """
    # Ensure the output directory exists before writing files
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{os.path.basename(pdf_path).replace('.pdf', '')}.xml")
    
    try:
        # Open the PDF for table extraction
        with pdfplumber.open(pdf_path) as pdf:
            root = ET.Element("pdf_tables")  # Root element for XML
            table_count = 0  # Counter for tables extracted

            # Iterate through each page in the PDF
            for page_number, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()  # Extract raw table data
                if tables:
                    # Process each table found on the page
                    for table_index, table in enumerate(tables, start=1):
                        table_count += 1
                        table_node = ET.SubElement(
                            root, "table", {"page": str(page_number), "table_number": str(table_index)})

                        # Get table bounding box coordinates if available
                        table_bbox = page.find_tables()[table_index - 1].bbox if page.find_tables() else None
                        if table_bbox:
                            x0, y0, x1, y1 = table_bbox
                            width = x1 - x0
                            height = y1 - y0
                            coordinates_text = f"{page_number},{x0:.2f},{y0:.2f},{width:.2f},{height:.2f}"
                        else:
                            coordinates_text = f"{page_number},no coordinates"

                        # Add coordinates info to XML
                        coordinates_node = ET.SubElement(table_node, "coordinates")
                        coordinates_node.text = coordinates_text

                        # Collect text above and below the table for context
                        words_above, words_below = [], []
                        for word in page.extract_words():
                            word_x0, word_y0, word_x1, word_y1 = (
                                word['x0'], word['top'], word['x1'], word['bottom'])
                            if table_bbox:
                                x0, y0, x1, y1 = table_bbox
                                # Check if word lies above the table within margin
                                if word_y1 <= y0 and x0 <= word_x0 <= x1 and (y0 - word_y1) <= max_margin:
                                    words_above.append(word['text'])
                                # Check if word lies below the table within margin
                                if word_y0 >= y1 and x0 <= word_x0 <= x1 and (word_y0 - y1) <= max_margin:
                                    words_below.append(word['text'])
                        above_text = " ".join(words_above)
                        below_text = " ".join(words_below)
                        context = f"Above: {above_text}".strip()
                        if below_text:
                            context += f" | Below: {below_text}"
                        context_node = ET.SubElement(table_node, "context")
                        context_node.text = context

                        # Add individual cell data under each row in XML
                        for row in table:
                            row_node = ET.SubElement(table_node, "row")
                            for cell in row:
                                cell_text = str(cell).strip() if cell and cell.strip() else "NAN"
                                cell_node = ET.SubElement(row_node, "cell")
                                cell_node.text = cell_text

            # Convert XML tree to string and format it
            xml_str = ET.tostring(root, encoding="utf-8").decode("utf-8")
            xml_str = xml_str.replace('<table', '\n<table')

            # Write XML output to file
            with open(output_file, "w", encoding="utf-8") as xml_file:
                xml_file.write(xml_str)
            # File is automatically closed after exiting the 'with' block
        return table_count
    except Exception as e:
        # Return error message for this PDF
        return f"Error processing {pdf_path}: {e}"

def read_total_tables(file_path):
    """
    Reads the expected number of tables from a text file.

    Args:
        file_path (str): Path to the text file containing the line 'Number of tables in PDF file: N'.

    Returns:
        int or None: The number of tables if found, otherwise None.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            match = re.search(r'Number of tables in PDF file: (\d+)', file.read())
            return int(match.group(1)) if match else None
        # File is automatically closed after exiting the 'with' block
    except FileNotFoundError:
        # If the file isn't found, return None to skip
        return None

def calculate_accuracy(extracted_tables, total_tables):
    """
    Computes accuracy of table extraction.

    Args:
        extracted_tables (int): Number of tables extracted by pdfplumber.
        total_tables (int): Actual number of tables in the PDF.

    Returns:
        float: Accuracy value between 0 and 1.
    """
    if total_tables == 0:
        return 0
    diff = abs(extracted_tables - total_tables)
    if extracted_tables <= total_tables:
        return max(0, 1 - diff / total_tables)
    else:
        return max(0, 1 - diff / extracted_tables)

def main(dataset_path):
    """
    Runs evaluation over a dataset of PDFs, logging extraction counts, accuracy, and timings.

    Args:
        dataset_path (str): Path to the root dataset folder containing subfolders '001' to '020'.
    """
    current_dir = os.getcwd()
    output_dir = os.path.join(current_dir, "Output_pdfplumber")
    results_dir = os.path.join(current_dir, "Results", "pdfplumber")
    os.makedirs(results_dir, exist_ok=True)
    log_file = os.path.join(results_dir, "pdfplumber_evaluation_log.txt")

    # Initialize summary counters
    total_comparisons = 0
    total_processing_time = 0
    total_tables_sum = 0
    extracted_tables_sum = 0
    total_accuracy_percent_sum = 0

    with open(log_file, "w", encoding="utf-8") as log:
        for i in range(1, 21):
            folder = f"{i:03d}"
            pdf_path = os.path.join(dataset_path, folder, f"{folder}.pdf")
            total_file = os.path.join(dataset_path, folder, f"TotalTables{i}.txt")
            if not os.path.isfile(pdf_path):
                # Skip missing PDFs gracefully
                continue

            # Process each PDF and measure time
            start = time.time()
            count = extract_tables_from_pdf(pdf_path, output_dir)
            proc_time = time.time() - start
            total_processing_time += proc_time

            # Get true table count and update summaries
            total = read_total_tables(total_file)
            total_tables_sum += total if total is not None else 0
            extracted_tables_sum += count

            # Calculate and accumulate accuracy
            accuracy = calculate_accuracy(count, total) * 100
            total_accuracy_percent_sum += accuracy

            # Compute time per table for this document
            time_per_table = proc_time / count if count > 0 else 0

            total_comparisons += 1

            # Log details for this PDF
            log.write(f"Processing folder: {folder}\n")
            log.write(f"PDF {folder}.pdf:\n")
            log.write(f"Extracted tables: {count}\n")
            log.write(f"Total tables: {total}\n")
            log.write(f"Accuracy = {accuracy:.2f}%\n")
            log.write(f"Processing time: {proc_time:.4f} seconds\n")
            log.write(f"Time per table: {time_per_table:.4f} seconds\n")
            log.write("\n" + "-"*50 + "\n")

            # Print only accuracy to console for quick feedback
            print(f"Processed {folder}: Accuracy {accuracy:.2f}%")

        # Compute final summary metrics
        avg_acc = total_accuracy_percent_sum / total_comparisons if total_comparisons else 0
        avg_time = total_processing_time / total_comparisons if total_comparisons else 0
        overall_acc = calculate_accuracy(extracted_tables_sum, total_tables_sum) * 100
        overall_time_per_table = total_processing_time / extracted_tables_sum if extracted_tables_sum > 0 else 0

        # Write summary to log
        log.write("\nSummary:\n")
        log.write(f"Total comparisons: {total_comparisons}\n")
        log.write(f"Total tables in all PDFs: {total_tables_sum}\n")
        log.write(f"Total tables found by pdfplumber: {extracted_tables_sum}\n")
        log.write(f"Overall accuracy: {overall_acc:.2f}%\n")
        log.write(f"Average accuracy per PDF-document: {avg_acc:.2f}%\n")
        log.write(f"Average processing time per PDF-document: {avg_time:.4f} seconds\n")
        log.write(f"Average processing time per table: {overall_time_per_table:.4f} seconds\n")
        log.write("\n# Accuracy explanation:\n")
        log.write("# Overall accuracy: Compares all tables found versus all actual tables in the dataset.\n")
        log.write("# Average accuracy per PDF-document: Calculates accuracy for each PDF separately, then averages those results.\n")
# File is automatically closed after exiting the 'with' block
if __name__ == "__main__":
    main("Dataset")