import difflib
import os
import torch
from PIL import Image
from transformers import VisionEncoderDecoderModel
from transformers.models.nougat import NougatTokenizerFast
from nougat_latex import NougatLaTexProcessor
import time


def normalize_latex(latex_string):
    """
    Normalize the LaTeX string by removing unnecessary spaces and ensuring consistent formatting.
    """
    latex_string = latex_string.replace(" ", "").replace("\\,", "").replace("\\ ", "")
    latex_string = latex_string.replace("...", "\\dots")  # Normalize ellipsis
    return latex_string


def compare_latex(correct_latex, ocr_latex):
    """
    Compare the correctness of the OCR output with the correct LaTeX expression.
    """
    # Normalize both strings
    normalized_correct = normalize_latex(correct_latex)
    normalized_ocr = normalize_latex(ocr_latex)

    # Use difflib to compare the two strings
    diff = difflib.ndiff(normalized_correct, normalized_ocr)
    similarity = sum(1 for c in diff if c[0] == " ") / len(normalized_correct)

    return similarity


def run_ocr_and_compare(img_path, txt_path, model, tokenizer, latex_processor, device):
    """
    Run OCR on the image and compare the result with the corresponding LaTeX in the text file.
    """
    # Start timer to measure OCR processing time
    start_time = time.time()

    # Open the image
    image = Image.open(img_path)
    if not image.mode == "RGB":
        image = image.convert("RGB")

    # Process image for model input
    pixel_values = latex_processor(image, return_tensors="pt").pixel_values
    decoder_input_ids = tokenizer(
        tokenizer.bos_token, add_special_tokens=False, return_tensors="pt"
    ).input_ids

    # Run OCR
    with torch.no_grad():
        outputs = model.generate(
            pixel_values.to(device),
            decoder_input_ids=decoder_input_ids.to(device),
            max_length=model.decoder.config.max_length,
            early_stopping=True,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
            use_cache=True,
            num_beams=5,
            bad_words_ids=[[tokenizer.unk_token_id]],
            return_dict_in_generate=True,
        )

    ocr_latex = tokenizer.batch_decode(outputs.sequences)[0]
    ocr_latex = ocr_latex.replace(tokenizer.eos_token, "").replace(tokenizer.pad_token, "").replace(tokenizer.bos_token, "")

    # End timer to calculate elapsed time
    elapsed_time = time.time() - start_time

    # Read the correct LaTeX from the corresponding .txt file
    with open(txt_path, "r") as file:
        correct_latex = file.read().strip()

    # Compare the LaTeX strings
    similarity_score = compare_latex(correct_latex, ocr_latex)

    return similarity_score, ocr_latex, correct_latex, elapsed_time


def process_dataset(dataset_dir, model, tokenizer, latex_processor, device, output_file):
    """
    Process the entire dataset, comparing OCR results with ground truth LaTeX and logging results.
    """
    passed_count = 0
    total_time = 0
    total_comparisons = 0
    total_similarity = 0

    # Open the output file to write results
    with open(output_file, "w") as f:
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
                        similarity_score, ocr_latex, correct_latex, elapsed_time = run_ocr_and_compare(
                            img_path, txt_path, model, tokenizer, latex_processor, device
                        )

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
        else:
            avg_time = 0

        # Calculating average similarity score
        avg_sim_score = total_similarity / total_comparisons

        # Writing summary
        f.write("\nSummary:\n")
        f.write(f"Total number of comparisons: {total_comparisons}\n")
        f.write(f"Number of passed comparisons(similarity > 0.9): {passed_count}\n")
        f.write(f"Percentage of passed comparisons: {passed_count/total_comparisons:.2%}\n")
        f.write(f"Average similarity score: {avg_sim_score:.4f}\n")
        f.write(f"Average OCR response time: {avg_time:.4f} seconds\n")


# Initialize the Nougat model and processor
model_name = "Norm/nougat-latex-base"
device = "cuda" if torch.cuda.is_available() else "cpu"

model = VisionEncoderDecoderModel.from_pretrained(model_name).to(device)
tokenizer = NougatTokenizerFast.from_pretrained(model_name)
latex_processor = NougatLaTexProcessor.from_pretrained(model_name)

# Define the root directory where your dataset is stored
dataset_dir = "/content/SmallImage2LatexOCR/Dataset"  # Change this path as needed

# Define the output file
output_file = "NougatLaTeXOCR_results.txt"

# Process the entire dataset and write results to the output file
process_dataset(dataset_dir, model, tokenizer, latex_processor, device, output_file)
