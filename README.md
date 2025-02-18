# Sci2XML

## Overview  
This repository provides a pipeline for converting research PDFs into structured XML using **Grobid**, a **custom classification model**, and specialized OCR tools. It supports multiple execution modes: **Streamlit UI**, **terminal**, and **code integration**.  

Developed as part of our **bachelor’s project in collaboration with Sintef** for the **enRichMyData** initiative.  

## Features  
- **Preprocessing with Grobid** to extract metadata and structure.  
- **Custom classification model** to validate extracted sections.  
- **Specialized OCR and data extraction tools**:  
  - **Sumen** – Converts formulas to LaTeX.  
  - **Unichart** – Extracts and summarizes chart data.  
  - **pdfplumber** – Parses tables accurately.  
- **Multiple execution modes**: Streamlit UI, terminal, and direct code usage.  

## Installation  
