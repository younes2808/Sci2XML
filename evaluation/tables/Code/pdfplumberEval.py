import pdfplumber
import os
import xml.etree.ElementTree as ET
import time
import re

def extract_tables_from_pdf(pdf_path, output_dir, max_margin=50):
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{os.path.basename(pdf_path).replace('.pdf', '')}.xml")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            root = ET.Element("pdf_tables")
            table_count = 0

            for page_number, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                if tables:
                    for table_index, table in enumerate(tables, start=1):
                        table_count += 1
                        table_node = ET.SubElement(root, "table", {"page": str(page_number), "table_number": str(table_index)})

                        # Hent koordinater for tabellen (bbox)
                        table_bbox = page.find_tables()[table_index - 1].bbox if page.find_tables() else None
                        if table_bbox:
                            x0, y0, x1, y1 = table_bbox
                            width = x1 - x0
                            height = y1 - y0
                            coordinates_text = f"{page_number},{x0:.2f},{y0:.2f},{width:.2f},{height:.2f}"
                        else:
                            coordinates_text = f"{page_number},Ingen koordinater funnet"

                        coordinates_node = ET.SubElement(table_node, "coordinates")
                        coordinates_node.text = coordinates_text

                        # Få kontekst (tekst over og under tabellen)
                        words_above = []
                        words_below = []
                        for word in page.extract_words():
                            word_x0, word_y0, word_x1, word_y1 = word['x0'], word['top'], word['x1'], word['bottom']
                            if word_y1 <= y0 and x0 <= word_x0 <= x1:
                                distance = y0 - word_y1
                                if distance <= max_margin:
                                    words_above.append(word['text'])
                            if word_y0 >= y1 and x0 <= word_x0 <= x1:
                                distance = word_y0 - y1
                                if distance <= max_margin:
                                    words_below.append(word['text'])
                        above_text = " ".join(words_above) if words_above else ""
                        below_text = " ".join(words_below) if words_below else ""
                        context = f"Text above table: {above_text}".strip()
                        if below_text:
                            context += f" | Text under table: {below_text}"
                        
                        context_node = ET.SubElement(table_node, "context")
                        context_node.text = context

                        # Legg til cellene i tabellen
                        for row in table:
                            row_node = ET.SubElement(table_node, "row")
                            for cell in row:
                                cell_text = str(cell) if cell is not None and cell.strip() else "NAN"
                                cell_node = ET.SubElement(row_node, "cell")
                                cell_node.text = cell_text

            # Generer XML-strengen uten linjeskift mellom elementene
            xml_str = ET.tostring(root, encoding="utf-8").decode("utf-8")
            xml_str = xml_str.replace('<table', '\n<table')  # Legg til linjeskift før tabellene

            # Lagre til fil
            with open(output_file, "w", encoding="utf-8") as xml_file:
                xml_file.write(xml_str)
        
            return table_count  # Returnerer antall tabeller
    except Exception as e:
        return f"Error processing {pdf_path}: {e}"

def read_total_tables(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            match = re.search(r'Number of tables in PDF file: (\d+)', content)
            if match:
                return int(match.group(1))
    except FileNotFoundError:
        return None
    return None

def calculate_accuracy(extracted_tables, total_tables):
    if total_tables == 0:
        return 0
    difference = abs(extracted_tables - total_tables)
    if extracted_tables <= total_tables:
        accuracy = 1 - (difference / total_tables)
    else:
        accuracy = 1 - (difference / extracted_tables)
    return max(0, accuracy)

def main(dataset_path):
    current_dir = os.getcwd()
    output_dir = os.path.join(current_dir, "Output_PDFplumber")
    results_dir = os.path.join(current_dir, "Results", "PDFplumber")
    os.makedirs(results_dir, exist_ok=True)
    log_file = os.path.join(results_dir, "pdfplumber_evaluation_log.txt")
    
    total_comparisons = 0
    passed_comparisons = 0
    total_similarity = 0
    total_processing_time = 0
    
    total_tables_sum = 0
    extracted_tables_sum = 0
    
    with open(log_file, "w", encoding="utf-8") as log:
        for i in range(1, 21):
            folder_name = f"{i:03d}"
            folder_path = os.path.join(dataset_path, folder_name)
            pdf_file = os.path.join(folder_path, f"{folder_name}.pdf")
            total_tables_file = os.path.join(folder_path, f"TotalTables{i}.txt")
            
            if os.path.isfile(pdf_file):
                start_time = time.time()
                extracted_tables = extract_tables_from_pdf(pdf_file, output_dir)
                processing_time = time.time() - start_time
                total_processing_time += processing_time
                
                total_tables = read_total_tables(total_tables_file)
                
                total_tables_sum += total_tables if total_tables is not None else 0
                extracted_tables_sum += extracted_tables
                
                accuracy = calculate_accuracy(extracted_tables, total_tables) * 100
                similarity = accuracy / 100
                
                total_comparisons += 1
                if similarity > 0.9:
                    passed_comparisons += 1
                total_similarity += similarity
                
                log.write(f"Processing folder: {folder_name}\n")
                log.write(f"PDF {folder_name}.pdf:\n")
                log.write(f"Extracted tables: {extracted_tables}\n")
                log.write(f"Total tables: {total_tables}\n")
                log.write(f"Similarity = {similarity * 100:.2f}%\n")  # Here we print similarity as percentage
                log.write(f"Processing time: {processing_time:.4f} seconds\n")
                log.write("\n" + "-" * 50 + "\n")
                
                print(f"Processed {folder_name}: Accuracy {accuracy:.2f}%")
            else:
                print(f"PDF not found in {folder_name}")
        
        average_similarity = total_similarity / total_comparisons if total_comparisons > 0 else 0
        average_processing_time = total_processing_time / total_comparisons if total_comparisons > 0 else 0
        overall_accuracy = calculate_accuracy(extracted_tables_sum, total_tables_sum) * 100
        
        log.write("\nSummary:\n")
        log.write(f"Total comparisons: {total_comparisons}\n")
        log.write(f"Total tables in all PDFs: {total_tables_sum}\n")
        log.write(f"Total tables found by PDFplumber: {extracted_tables_sum}\n")
        log.write(f"Overall accuracy: {overall_accuracy:.2f}%\n")
        log.write(f"Average similarity score: {average_similarity * 100:.2f}%\n")  # Formatting as percentage
        log.write(f"Average processing time: {average_processing_time:.4f} seconds\n")

if __name__ == "__main__":
    dataset_dir = "Dataset"
    main(dataset_dir)
