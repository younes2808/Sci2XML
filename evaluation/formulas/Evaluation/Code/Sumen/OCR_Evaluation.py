import torch
import os
import difflib
import time
from PIL import Image
from transformers import AutoProcessor, VisionEncoderDecoderModel

# Initialize the Sumen OCR model
def initialize_sumen_model():
    """
    Load the Sumen VisionEncoderDecoder model and processor.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = VisionEncoderDecoderModel.from_pretrained('hoang-quoc-trung/sumen-base').to(device)
    processor = AutoProcessor.from_pretrained('hoang-quoc-trung/sumen-base')
    return model, processor, device

# Normalize LaTeX
def normalize_latex(latex_string):
    """
    Normalize the LaTeX string by removing unnecessary spaces and ensuring consistent formatting.
    """
    latex_string = latex_string.replace(" ", "").replace("\\,", "").replace("\\ ", "")
    latex_string = latex_string.replace("...", "\\dots")  # Normalize ellipsis
    return latex_string

# Compare LaTeX similarity
def compare_latex(correct_latex, ocr_latex):
    """
    Compare the OCR output LaTeX with the ground truth LaTeX.
    """
    normalized_correct = normalize_latex(correct_latex)
    normalized_ocr = normalize_latex(ocr_latex)

    # Use difflib to compute similarity
    matcher = difflib.SequenceMatcher(None, normalized_correct, normalized_ocr)
    return matcher.ratio()

# Run Sumen OCR on an image
def run_sumen_ocr(img_path, model, processor, device):
    """
    Perform OCR on a single image using the Sumen model.
    """
    # Load and process the image
    image = Image.open(img_path).convert('RGB')
    pixel_values = processor.image_processor(image, return_tensors="pt").pixel_values

    # Generate the LaTeX expression
    task_prompt = processor.tokenizer.bos_token
    decoder_input_ids = processor.tokenizer(
        task_prompt, add_special_tokens=False, return_tensors="pt"
    ).input_ids

    with torch.no_grad():
        outputs = model.generate(
            pixel_values.to(device),
            decoder_input_ids=decoder_input_ids.to(device),
            max_length=model.decoder.config.max_length,
            pad_token_id=processor.tokenizer.pad_token_id,
            eos_token_id=processor.tokenizer.eos_token_id,
            use_cache=True,
            num_beams=4,
            bad_words_ids=[[processor.tokenizer.unk_token_id]],
            return_dict_in_generate=True,
        )
    ocr_latex = processor.tokenizer.batch_decode(outputs.sequences)[0]
    ocr_latex = ocr_latex.replace(
        processor.tokenizer.eos_token, ""
    ).replace(
        processor.tokenizer.pad_token, ""
    ).replace(processor.tokenizer.bos_token, "")
    return ocr_latex

# Process dataset
def process_dataset(dataset_dir, model, processor, device, output_file):
    """
    Process the dataset, comparing Sumen OCR output with ground truth LaTeX.
    """
    passed_count = 0
    total_time = 0
    total_comparisons = 0
    total_similarity = 0

    # Open the output file to write results
    with open(output_file, 'w') as f:
        for i in range(101):  # Process folders 000 to 100
            folder_name = f"{str(i).zfill(3)}"
            folder_path = os.path.join(dataset_dir, folder_name)

            if os.path.isdir(folder_path):  # Only process directories
                f.write(f"Processing folder: {folder_name}\n")

                # Process images and corresponding text files
                for j in range(101):  # Process files 000.png to 100.png
                    img_name = f"{str(j).zfill(3)}.png"
                    txt_name = f"{str(j).zfill(3)}.txt"

                    img_path = os.path.join(folder_path, img_name)
                    txt_path = os.path.join(folder_path, txt_name)

                    if os.path.exists(img_path) and os.path.exists(txt_path):
                        # Read the ground truth LaTeX
                        with open(txt_path, "r") as file:
                            correct_latex = file.read().strip()

                        # Start timer
                        start_time = time.time()

                        # Run OCR
                        ocr_latex = run_sumen_ocr(img_path, model, processor, device)

                        # End timer
                        elapsed_time = time.time() - start_time

                        # Compare OCR output with ground truth
                        similarity_score = compare_latex(correct_latex, ocr_latex)

                        # Write detailed results to the file
                        f.write(f"Folder {folder_name}, Image {img_name}: Similarity = {similarity_score:.4f}\n")
                        f.write(f"OCR LaTeX: {ocr_latex}\n")
                        f.write(f"Correct LaTeX: {correct_latex}\n")
                        f.write(f"Time taken for OCR: {elapsed_time:.4f} seconds\n")

                        if similarity_score > 0.95:
                            f.write("OCR output is highly accurate.\n")
                        elif similarity_score > 0.85:
                            f.write("OCR output is fairly accurate.\n")
                        else:
                            f.write("OCR output has significant differences.\n")

                        f.write("-" * 50 + "\n")

                        # Count the number of passed results
                        if similarity_score > 0.9:
                            passed_count += 1

                        # Update totals for averages
                        total_time += elapsed_time
                        total_comparisons += 1
                        total_similarity += similarity_score

        # Write summary
        if total_comparisons > 0:
            avg_time = total_time / total_comparisons
            avg_similarity = total_similarity / total_comparisons
        else:
            avg_time = 0
            avg_similarity = 0

        f.write("\nSummary:\n")
        f.write(f"Total comparisons: {total_comparisons}\n")
        f.write(f"Passed comparisons (similarity > 0.9): {passed_count}\n")
        f.write(f"Percentage passed: {100 * passed_count / total_comparisons:.2f}%\n")
        f.write(f"Average similarity score: {avg_similarity:.4f}\n")
        f.write(f"Average OCR time: {avg_time:.4f} seconds\n")

# Main execution
if __name__ == "__main__":
    # Initialize the model
    model, processor, device = initialize_sumen_model()

    # Define dataset directory and output file
    dataset_dir = "./../../../Dataset/"  # Change this to the correct dataset path
    output_file = "SumenOCR_Evaluation.txt"

    # Process the dataset
    process_dataset(dataset_dir, model, processor, device, output_file)
