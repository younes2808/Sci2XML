# Evaluating Table Extraction: pdfplumber vs. GROBID

This repository contains evaluation scripts to assess two tools, [pdfplumber](https://github.com/jsvine/pdfplumber) and [GROBID](https://github.com/kermitt2/GROBID), for extracting tables from PDF documents. The evaluation is performed on a small dataset of 20 PDFs where the number of tables in each document has been manually annotated.

## Dataset Description

The dataset is organized in a folder called `Dataset`, which contains 20 subfolders named from `001` to `020`. Each subfolder includes:

- **PDF File:** Named after the folder (e.g., `001.pdf` in folder `001`).
- **Text File:** A TXT file (e.g., `TotalTables1.txt`) containing the manually counted number of tables in the PDF. The content should follow this format:
  Number of tables in PDF file: X

## Purpose

The goal of this project is to benchmark and compare the performance of pdfplumber and GROBID in extracting tables from PDF documents. The evaluation consists of:

- Extracting tables along with metadata such as coordinates and surrounding context.
- Comparing the extracted table counts with manual annotations.
- Measuring processing time and computing an accuracy metric based on the difference between the extracted and annotated table counts.

## Evaluation

The evaluation is done using two Python scripts found in the `Code` folder:

- `pdfplumberEval.py`
- `grobidEval.py`

Both scripts loop through the dataset and compare extracted tables against manually annotated counts.

Detailed evaluation results, including the number of extracted tables, accuracy metrics, and processing times, are available in the Results folder.

Both tools were executed locally on the same machine under similar conditions to ensure a fair comparison.

## Environment Requirements

- **Python Version:** 3.6 or higher.
- **Required Packages:**  
  Install the necessary Python packages using:

```bash
pip install pdfplumber requests
```

## Results

![Table Results](https://github.com/user-attachments/assets/3da0a462-15a6-4a32-9de2-34dfdd12a649)
