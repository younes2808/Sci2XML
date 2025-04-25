import os
import requests
import time
import re

def process_pdf(file_path, grobid_url="http://localhost:8070/api/processFulltextDocument"):
    """
    Sends a PDF file to the GROBID service for full text processing.
    
    Args:
        file_path (str): The path to the PDF file.
        grobid_url (str): URL of the GROBID API endpoint.

    Returns:
        str: The XML response as a string, or an error message if something fails.
    """
    params = {
        "consolidateHeader": 1,
        "consolidateCitations": 1,
        "consolidateFunders": 1,
        "includeRawAffiliations": 1,
        "includeRawCitations": 1,
        "segmentSentences": 1,
        "teiCoordinates": [
            "ref", "s", "biblStruct", "persName", "figure",
            "formula", "head", "note", "title", "affiliation"
        ]
    }

    try:
        with open(file_path, 'rb') as pdf_file:
            files = {'input': pdf_file}
            response = requests.post(grobid_url, files=files, data=params)
            response.raise_for_status()
            return response.text
        # File is automatically closed after exiting the 'with' block
    except requests.exceptions.RequestException as e:
        return f"Feil ved behandling av PDF: {e}"
    except FileNotFoundError:
        return "PDF-filen ble ikke funnet. Sjekk filstien og prøv igjen."

def count_tables_in_xml(xml_content):
    """
    Counts the number of <figure> tags with type="table" in the XML content.

    Args:
        xml_content (str): The XML content returned from GROBID.

    Returns:
        int: The number of tables found.
    """
    return len(re.findall(r'<figure[^>]*\s+type="table"[^>]*>', xml_content))

def read_total_tables(file_path):
    """
    Reads the number of tables from a txt file.

    Args:
        file_path (str): Path to the text file containing the total number of tables.

    Returns:
        int or None: The number of tables if found, otherwise None.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            match = re.search(r'Number of tables in PDF file: (\d+)', content)
            if match:
                return int(match.group(1))
        # File is automatically closed after exiting the 'with' block
    except FileNotFoundError:
        return None
    return None

def calculate_accuracy(grobid_tables, total_tables):
    """
    Calculates the accuracy of table detection by GROBID.

    Args:
        grobid_tables (int): The number of tables detected by GROBID.
        total_tables (int): The actual number of tables in the PDF.

    Returns:
        float: Accuracy score between 0 and 1.
    """
    if total_tables == 0:
        return 0

    difference = abs(grobid_tables - total_tables)

    if grobid_tables <= total_tables:
        accuracy = 1 - (difference / total_tables)
    else:
        accuracy = 1 - (difference / grobid_tables)

    return max(0, accuracy)

def main(dataset_path):
    """
    Evaluates GROBID's table extraction accuracy across a dataset of PDFs.

    Args:
        dataset_path (str): Path to the dataset directory containing PDF folders.
    """
    current_dir = os.getcwd()

    results_dir = os.path.join(current_dir, "Results", "Grobid")
    os.makedirs(results_dir, exist_ok=True)
    log_file = os.path.join(results_dir, "grobid_evaluation_log.txt")

    output_dir = os.path.join(current_dir, "Output_Grobid")
    os.makedirs(output_dir, exist_ok=True)

    total_comparisons = 0
    passed_comparisons = 0
    total_processing_time = 0

    # Summary variables
    total_tables_sum = 0
    grobid_tables_sum = 0
    total_accuracy_percent_sum = 0

    with open(log_file, "w", encoding="utf-8") as log:
        for i in range(1, 21):
            folder_name = f"{i:03d}"
            folder_path = os.path.join(dataset_path, folder_name)
            pdf_file = os.path.join(folder_path, f"{folder_name}.pdf")
            total_tables_file = os.path.join(folder_path, f"TotalTables{i}.txt")
            output_xml_file = os.path.join(output_dir, f"{folder_name}.xml")

            if os.path.isfile(pdf_file):
                start_time = time.time()
                xml_content = process_pdf(pdf_file)
                processing_time = time.time() - start_time
                total_processing_time += processing_time

                with open(output_xml_file, "w", encoding="utf-8") as output_file:
                    output_file.write(xml_content)
                grobid_tables = count_tables_in_xml(xml_content)
                total_tables = read_total_tables(total_tables_file)

                # Update summary values
                total_tables_sum += total_tables if total_tables is not None else 0
                grobid_tables_sum += grobid_tables

                # Accuracy in percentage
                accuracy = calculate_accuracy(grobid_tables, total_tables) * 100
                total_accuracy_percent_sum += accuracy

                # Time per table
                time_per_table = processing_time / grobid_tables if grobid_tables > 0 else 0

                total_comparisons += 1
                if accuracy > 90:
                    passed_comparisons += 1

                # Log per document
                log.write(f"Processing folder: {folder_name}\n")
                log.write(f"Folder {folder_name}, PDF {folder_name}.pdf:\n")
                log.write(f"GROBID tables: {grobid_tables}\n")
                log.write(f"Total tables: {total_tables}\n")
                log.write(f"Accuracy = {accuracy:.2f}%\n")
                log.write(f"Time taken for processing: {processing_time:.4f} seconds\n")
                log.write(f"Time per table: {time_per_table:.4f} seconds\n")
                log.write("\n" + "-" * 50 + "\n")

                print(f"Processed {folder_name}: Accuracy {accuracy:.2f}%")
            else:
                print(f"PDF not found in {folder_name}")

        # Final summary
        average_accuracy_percent = total_accuracy_percent_sum / total_comparisons if total_comparisons > 0 else 0
        average_processing_time = total_processing_time / total_comparisons if total_comparisons > 0 else 0
        overall_accuracy = calculate_accuracy(grobid_tables_sum, total_tables_sum) * 100
        overall_time_per_table = total_processing_time / grobid_tables_sum if grobid_tables_sum > 0 else 0

        log.write("\nSummary:\n")
        log.write(f"Total number of comparisons: {total_comparisons}\n")
        log.write(f"Total tables in all PDFs: {total_tables_sum}\n")
        log.write(f"Total tables found by GROBID: {grobid_tables_sum}\n")
        log.write(f"Overall accuracy: {overall_accuracy:.2f}%\n")
        log.write(f"Average accuracy per PDF-document: {average_accuracy_percent:.2f}%\n")
        log.write(f"Average processing time per PDF-document: {average_processing_time:.4f} seconds\n")
        log.write(f"Average processing time per table: {overall_time_per_table:.4f} seconds\n")
        log.write("\n# Accuracy explanation:\n")

        log.write("# Overall accuracy: Compares all tables found versus all actual tables in the dataset.\n")
        log.write("# Average accuracy per PDF-document: Calculates accuracy for each PDF separately, then averages those results.\n")
        
# File is automatically closed after exiting the 'with' block
if __name__ == "__main__":
    dataset_dir = "Dataset"
    main(dataset_dir)
