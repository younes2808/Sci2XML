import os
import requests
import time
import re

def process_pdf(file_path, grobid_url="http://localhost:8070/api/processFulltextDocument"):
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
    return len(re.findall(r'<figure[^>]*\s+type="table"[^>]*>', xml_content))

def read_total_tables(file_path):
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
    if total_tables == 0:
        return 0
    
    difference = abs(grobid_tables - total_tables)
    
    if grobid_tables <= total_tables:
        accuracy = 1 - (difference / total_tables)
    else:
        accuracy = 1 - (difference / grobid_tables)
    
    return max(0, accuracy)

def main(dataset_path):
    current_dir = os.getcwd()
    
    results_dir = os.path.join(current_dir, "Results", "Grobid")
    os.makedirs(results_dir, exist_ok=True)
    log_file = os.path.join(results_dir, "grobid_evaluation_log.txt")
    
    output_dir = os.path.join(current_dir, "Output_Grobid")
    os.makedirs(output_dir, exist_ok=True)
    
    total_comparisons = 0
    passed_comparisons = 0
    total_processing_time = 0

    # Summeringsvariabler for accuracy og tabeller
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
                # File is automatically closed after exiting the 'with' block
                
                grobid_tables = count_tables_in_xml(xml_content)
                total_tables = read_total_tables(total_tables_file)
                
                # Oppdater summeringsvariabler
                total_tables_sum += total_tables if total_tables is not None else 0
                grobid_tables_sum += grobid_tables
                
                # Beregn nøyaktighet (%) per dokument
                accuracy = calculate_accuracy(grobid_tables, total_tables) * 100
                total_accuracy_percent_sum += accuracy
                
                # Beregn tid per tabell
                time_per_table = processing_time / grobid_tables if grobid_tables > 0 else 0
                
                total_comparisons += 1
                if accuracy > 90:
                    passed_comparisons += 1
                
                # Log resultat per dokument
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

        # Oppsummering
        average_accuracy_percent = total_accuracy_percent_sum / total_comparisons if total_comparisons > 0 else 0
        average_processing_time = total_processing_time / total_comparisons if total_comparisons > 0 else 0
        overall_accuracy = calculate_accuracy(grobid_tables_sum, total_tables_sum) * 100
        
        log.write("\nSummary:\n")
        log.write(f"Total number of comparisons: {total_comparisons}\n")
        log.write(f"Total tables in all PDFs: {total_tables_sum}\n")
        log.write(f"Total tables found by GROBID: {grobid_tables_sum}\n")
        log.write(f"Overall accuracy: {overall_accuracy:.2f}%\n")
        log.write(f"Average accuracy per document: {average_accuracy_percent:.2f}%\n")
        log.write(f"Average processing time: {average_processing_time:.4f} seconds\n")
        log.write("\n# Accuracy explanation:\n")
        log.write("# Overall accuracy: Measures accuracy by comparing the total number of found tables with the total number of true tables across the entire dataset as one combined metric.\n")
        log.write("# Average accuracy per document: The average of the individual accuracy percentages calculated for each PDF, where each file is weighted equally.\n")
    # File is automatically closed after exiting the 'with' block

if __name__ == "__main__":
    dataset_dir = "Dataset"
    main(dataset_dir)