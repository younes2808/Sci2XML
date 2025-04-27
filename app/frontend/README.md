# Frontend

This folder contains the files related to the frontend of the project.

## Files

- **app.py:** This Python script serves as the core interface for the web application, built using Streamlit for an interactive user experience. Its primary purpose is to extract, process, and display scientific papers in PDF format, utilizing GROBID for automatic metadata extraction. Additionally, the script includes various functions for updating XML text areas, cleaning LaTeX formulas, reading and modifying environment files, parsing the uploaded PDF file with GROBID, and processing the classifier. The script follows a structured flow, with the main function performing the following steps:
    1. Initializes the UI with a custom design using st.markdown and applies the provided css.html file.
    2. Accepts a scientific paper in PDF format uploaded by the user.
    3. Sends the PDF to GROBID for metadata extraction and parsing.
    4. Displays the GROBID output both as a rendered PDF and an editable XML text.
    5. Allows the user to modify the XML, if necessary.
    6. Allows the user to include description of formulas, if desirable.
    7. Processes the XML by invoking the process_classifier, which classifies and interprets the document's structure.
    8. Displays the interpreted results in views for each element type as well an editable XML text.
    9. Enables the user to refine and download the final XML file.

- **css.html:** This file is a block of custom CSS designed to style and modify the appearance of a Streamlit web app. It uses Streamlit’s internal data-testid attributes to target specific UI components and override their default styles.

- **frontendmodule.py:** This Python file is a script designed to interact with various web services (like Localtunnel, ngrok, and Streamlit) to expose local applications or APIs to the public internet. It includes logging and environment variable handling for secure configuration. The script primarily performs two key tasks:
    1. Starting Streamlit: Runs a Streamlit app and tunnels the local port (8501) using either Localtunnel or ngrok.    
    2. Starting API: Starts a backend API service and exposes it to the public internet via the selected tunnel provider.