![Skjermbilde 2025-02-18 142502](https://github.com/user-attachments/assets/b2e499ca-9391-4b74-b18a-2029ea8e5284)
---
[![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Streamlit](https://img.shields.io/badge/Framework-Streamlit-red)](https://streamlit.io/)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
## Overview  
This repository provides a pipeline for converting research PDFs into structured XML using [**Grobid**](https://github.com/kermitt2/grobid), a **custom classification model**, and specialized OCR tools. It supports multiple execution modes: **Streamlit UI**, **terminal**, and **code integration**.  

Developed as part of our **bachelor’s project in collaboration with SINTEF** for the [**enRichMyData**](https://www.sintef.no/en/projects/2022/enrichmydata/) initiative.  

## Features  
- **Preprocessing with Grobid** to extract metadata and structure.  
- **Custom classification model** to validate extracted sections.  
- **Specialized OCR and data extraction tools**:  
  - [**Sumen**](https://github.com/hoang-quoc-trung/sumen) – Converts formulas to LaTeX.  
  - [**Unichart**](https://github.com/vis-nlp/UniChart) – Extracts and summarizes chart data.  
  - [**pdfplumber**](https://github.com/jsvine/pdfplumber) – Parses tables accurately.  
- **Multiple execution modes**: Streamlit UI, terminal, and direct code usage.  

## Installation  

## Contributors  

- [Morten Nilsen](https://github.com/SameNilsen)  
- [Jan Axel Støre Ørmen](https://github.com/axelsormen)
- [Rafey Ul-Islam Afzal](https://github.com/R4f3y)  
- [Shoeb Mohammadi](https://github.com/shoeb03)  
- [Younes Benhaida](https://github.com/younes2808)

## Acknowledgements  
We thank the developers and contributors of [pdfplumber](https://github.com/jsvine/pdfplumber), [Grobid](https://github.com/kermitt2/grobid), [Sumen](https://github.com/hoang-quoc-trung/sumen), and [Unichart](https://github.com/vis-nlp/UniChart) for their invaluable tools and contributions to document processing. This project would not have been possible without their dedication to open-source innovation. Thank you!
