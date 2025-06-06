import os
from PIL import Image
from transformers import AutoTokenizer, VisionEncoderDecoderModel, AutoImageProcessor
import difflib
import time

# Initialize MixTex Model
feature_extractor = AutoImageProcessor.from_pretrained("MixTex/ZhEn-Latex-OCR")
tokenizer = AutoTokenizer.from_pretrained("MixTex/ZhEn-Latex-OCR", max_len=296)
model = VisionEncoderDecoderModel.from_pretrained("MixTex/ZhEn-Latex-OCR")

# Function to clean OCR output
def clean_ocr_output(ocr_latex):
    """
    Clean the OCR LaTeX output by removing unnecessary tags and formatting.
    """
    ocr_latex = ocr_latex.replace("<s><s>\\begin{align*}", "").replace("\\end{align*}</s>", "")
    ocr_latex = ocr_latex.strip()  # Remove leading/trailing whitespace
    return ocr_latex

# Function to normalize LaTeX
def normalize_latex(latex_string):
    """
    Normalize the LaTeX string by removing unnecessary spaces and ensuring consistent formatting.
    """
    latex_string = latex_string.replace(" ", "").replace("\\,", "").replace("\\ ", "")
    latex_string = latex_string.replace("...", "\\dots")  # Normalize ellipsis
    return latex_string

# Function to compare LaTeX strings
def compare_latex(correct_latex, ocr_latex):
    """
    Compare the correctness of the OCR output with the correct LaTeX expression.
    """
    # Normalize both strings
    normalized_correct = normalize_latex(correct_latex)
    normalized_ocr = normalize_latex(ocr_latex)

    # Use difflib to compare the two strings
    diff = difflib.ndiff(normalized_correct, normalized_ocr)
    similarity = sum(1 for c in diff if c[0] == ' ') / len(normalized_correct)

    return similarity

# Function to run OCR and compare results
def run_ocr_and_compare(img_path, txt_path):
    """
    Run OCR on the image and compare the result with the corresponding LaTeX in the text file.
    """
    # Start timer to measure OCR processing time
    start_time = time.time()

    # Open the image
    img = Image.open(img_path)
    pixel_values = feature_extractor(img, return_tensors="pt").pixel_values

    # Generate OCR output
    with torch.no_grad():
        ocr_output = model.generate(pixel_values)
        ocr_latex = tokenizer.decode(ocr_output[0], skip_special_tokens=True)
        ocr_latex = clean_ocr_output(ocr_latex)  # Clean the OCR output

    # End timer to calculate elapsed time
    elapsed_time = time.time() - start_time

    # Read the correct LaTeX from the corresponding .txt file
    with open(txt_path, "r") as file:
        correct_latex = file.read().strip()
    # File is automatically closed after exiting the 'with' block

    # Compare the LaTeX strings
    similarity_score = compare_latex(correct_latex, ocr_latex)

    return similarity_score, ocr_latex, correct_latex, elapsed_time

# Function to process dataset
def process_dataset(dataset_dir, output_file):
    """
    Process the entire dataset, comparing OCR results with ground truth LaTeX and logging results.
    """
    passed_count = 0
    total_time = 0
    total_comparisons = 0
    total_similarity = 0

    # Open the output file to write results
    with open(output_file, 'w') as f:
        # Loop through all folders from 000 to 100
        for i in range(101):  # 0 to 100
            folder_name = f"{str(i).zfill(3)}"  # Format as 000, 001, ..., 100
            folder_path = os.path.join(dataset_dir, folder_name)

            if os.path.isdir(folder_path):  # Process only directories
                f.write(f"Processing folder: {folder_name}\n")
                # Loop through all image files from 000.png to 100.png
                for j in range(101):  # 0 to 100
                    img_name = f"{str(j).zfill(3)}.png"
                    txt_name = f"{str(j).zfill(3)}.txt"

                    img_path = os.path.join(folder_path, img_name)
                    txt_path = os.path.join(folder_path, txt_name)

                    if os.path.exists(img_path) and os.path.exists(txt_path):
                        similarity_score, ocr_latex, correct_latex, elapsed_time = run_ocr_and_compare(img_path, txt_path)

                        f.write(f"Folder {folder_name}, Image {img_name}: Similarity = {similarity_score:.4f}\n")
                        f.write(f"OCR LaTeX: {ocr_latex}\n")
                        f.write(f"Correct LaTeX: {correct_latex}\n")
                        f.write(f"Time taken for OCR: {elapsed_time:.4f} seconds\n")

                        # Provide feedback based on similarity score
                        if similarity_score > 0.95:
                            f.write("OCR output is highly accurate.\n")
                        elif similarity_score > 0.85:
                            f.write("OCR output is fairly accurate.\n")
                        else:
                            f.write("OCR output has significant differences.\n")

                        f.write("-" * 50 + "\n")

                        # Count the number of "passed" results (similarity > 0.9)
                        if similarity_score > 0.9:
                            passed_count += 1

                        # Accumulate total time for calculating average and similarity score
                        total_time += elapsed_time
                        total_comparisons += 1
                        total_similarity += similarity_score

        # After processing all files, write the summary to the output file
        if total_comparisons > 0:
            avg_time = total_time / total_comparisons
            avg_sim_score = total_similarity / total_comparisons
        else:
            avg_time = 0
            avg_sim_score = 0

        # Writing summary
        f.write("\nSummary:\n")
        f.write(f"Total number of comparisons: {total_comparisons}\n")
        f.write(f"Number of passed comparisons (similarity > 0.9): {passed_count}\n")
        f.write(f"Percentage of passed comparisons: {passed_count / total_comparisons * 100:.2f}%\n")
        f.write(f"Average similarity score: {avg_sim_score:.4f}\n")
        f.write(f"Average OCR response time: {avg_time:.4f} seconds\n")
    # File is automatically closed after exiting the 'with' block

# Define the root directory where your dataset is stored
dataset_dir = "/content/SmallImage2LatexOCR/Dataset"  # Change this path as needed

# Define the output file
output_file = "LaTeXOCR_Evaluation.txt"

# Process the entire dataset and write results to the output file
process_dataset(dataset_dir, output_file)
