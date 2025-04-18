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
                        words_above, words_below = [], []
                        for word in page.extract_words():
                            word_x0, word_y0, word_x1, word_y1 = word['x0'], word['top'], word['x1'], word['bottom']
                            if table_bbox:
                                x0, y0, x1, y1 = table_bbox
                                if word_y1 <= y0 and x0 <= word_x0 <= x1:
                                    distance = y0 - word_y1
                                    if distance <= max_margin:
                                        words_above.append(word['text'])
                                if word_y0 >= y1 and x0 <= word_x0 <= x1:
                                    distance = word_y0 - y1
                                    if distance <= max_margin:
                                        words_below.append(word['text'])
                        above_text = " ".join(words_above)
                        below_text = " ".join(words_below)
                        context = f"Text above table: {above_text}".strip()
                        if below_text:
                            context += f" | Text under table: {below_text}"
                        context_node = ET.SubElement(table_node, "context")
                        context_node.text = context

                        # Legg til cellene i tabellen
                        for row in table:
                            row_node = ET.SubElement(table_node, "row")
                            for cell in row:
                                cell_text = str(cell).strip() if cell and cell.strip() else "NAN"
                                cell_node = ET.SubElement(row_node, "cell")
                                cell_node.text = cell_text

            xml_str = ET.tostring(root, encoding="utf-8").decode("utf-8")
            xml_str = xml_str.replace('<table', '\n<table')

            with open(output_file, "w", encoding="utf-8") as xml_file:
                xml_file.write(xml_str)
        return table_count
    except Exception as e:
        return f"Error processing {pdf_path}: {e}"

def read_total_tables(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            match = re.search(r'Number of tables in PDF file: (\d+)', file.read())
            return int(match.group(1)) if match else None
    except FileNotFoundError:
        return None

def calculate_accuracy(extracted_tables, total_tables):
    if total_tables == 0:
        return 0
    diff = abs(extracted_tables - total_tables)
    if extracted_tables <= total_tables:
        return max(0, 1 - diff / total_tables)
    else:
        return max(0, 1 - diff / extracted_tables)

def main(dataset_path):
    current_dir = os.getcwd()
    output_dir = os.path.join(current_dir, "Output_PDFplumber")
    results_dir = os.path.join(current_dir, "Results", "PDFplumber")
    os.makedirs(results_dir, exist_ok=True)
    log_file = os.path.join(results_dir, "pdfplumber_evaluation_log.txt")

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
                continue

            start = time.time()
            count = extract_tables_from_pdf(pdf_path, output_dir)
            proc_time = time.time() - start
            total_processing_time += proc_time

            total = read_total_tables(total_file)
            total_tables_sum += total if total is not None else 0
            extracted_tables_sum += count

            accuracy = calculate_accuracy(count, total) * 100
            total_accuracy_percent_sum += accuracy

            time_per_table = proc_time / count if count > 0 else 0

            total_comparisons += 1
            if accuracy > 90:
                pass

            log.write(f"Processing folder: {folder}\n")
            log.write(f"PDF {folder}.pdf:\n")
            log.write(f"Extracted tables: {count}\n")
            log.write(f"Total tables: {total}\n")
            log.write(f"Accuracy = {accuracy:.2f}%\n")
            log.write(f"Processing time: {proc_time:.4f} seconds\n")
            log.write(f"Time per table: {time_per_table:.4f} seconds\n")
            log.write("\n" + "-"*50 + "\n")

            # console only accuracy
            print(f"Processed {folder}: Accuracy {accuracy:.2f}%")

        avg_acc = total_accuracy_percent_sum / total_comparisons if total_comparisons else 0
        avg_time = total_processing_time / total_comparisons if total_comparisons else 0
        overall_acc = calculate_accuracy(extracted_tables_sum, total_tables_sum) * 100

        log.write("\nSummary:\n")
        log.write(f"Total comparisons: {total_comparisons}\n")
        log.write(f"Total tables in all PDFs: {total_tables_sum}\n")
        log.write(f"Total tables found by PDFplumber: {extracted_tables_sum}\n")
        log.write(f"Overall accuracy: {overall_acc:.2f}%\n")
        log.write(f"Average accuracy per document: {avg_acc:.2f}%\n")
        log.write(f"Average processing time: {avg_time:.4f} seconds\n")
        log.write("\n# Accuracy explanation:\n")
        log.write("# Overall accuracy: Measures accuracy by comparing the total number of found tables with the total number of true tables across the entire dataset as one combined metric.\n")
        log.write("# Average accuracy per document: The average of the individual accuracy percentages calculated for each PDF, where each file is weighted equally.\n")


if __name__ == "__main__":
    main("Dataset")
