import torch
from transformers import DonutProcessor, VisionEncoderDecoderModel, AutoProcessor

# Determine the computation device: use GPU (CUDA) if available; otherwise, default to CPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def load_Sumen():
    """
    Load the Sumen model and processor.

    Sumen is an OCR (Optical Character Recognition) model optimized for document understanding tasks.
    This function loads the pre-trained model and the associated processor for handling image inputs.

    Returns:
        model (VisionEncoderDecoderModel): Pre-trained Sumen OCR model.
        processor (AutoProcessor): Processor for image preprocessing and text tokenization.
    """

    # Inform the user that the model is being loaded
    print("\n\n#-------------------- # Loading Sumen OCR model # ------------------#\n")

    # Load the Sumen model from the Hugging Face repository and move it to the appropriate device
    global sumen_model, sumen_processor  # Declare global variables for model persistence
    sumen_model = VisionEncoderDecoderModel.from_pretrained("hoang-quoc-trung/sumen-base").to(device)

    # Load the processor responsible for image preprocessing and text tokenization
    sumen_processor = AutoProcessor.from_pretrained("hoang-quoc-trung/sumen-base")

    # Confirm successful model and processor loading
    print("-----> Sumen model loaded successfully!")

    return sumen_model, sumen_processor  # Return the loaded model and processor

def run_sumen_ocr(image):
    """
    Perform OCR using the Sumen model on a given image.

    This function takes an image as input, processes it using the Sumen OCR model, and returns the extracted text in LaTeX format.

    Parameters:
    image (PIL.Image or tensor): Input image to be processed by the OCR model.

    Returns:
    clean_latex (str): The extracted text in LaTeX format, with unnecessary tokens removed.    
    """
    # Preprocess the image: convert it into pixel values compatible with the model
    pixel_values = sumen_processor.image_processor(image, return_tensors="pt").pixel_values.to(device)
    
    # Define the task prompt using the beginning-of-sequence (BOS) token
    task_prompt = sumen_processor.tokenizer.bos_token
    decoder_input_ids = sumen_processor.tokenizer(task_prompt, add_special_tokens=False, return_tensors="pt").input_ids
    
    # Perform inference in a no-gradient context to optimize performance
    with torch.no_grad():
        outputs = sumen_model.generate(
            pixel_values,  # Processed image input
            decoder_input_ids=decoder_input_ids.to(device),
            max_length=sumen_model.decoder.config.max_length,
            pad_token_id=sumen_processor.tokenizer.pad_token_id,
            eos_token_id=sumen_processor.tokenizer.eos_token_id,
            use_cache=True,  
            num_beams=4, 
            bad_words_ids=[[sumen_processor.tokenizer.unk_token_id]],  # Prevent unknown tokens from appearing
            return_dict_in_generate=True,  # Return structured output
        )
    # Decode the generated sequence into a human-readable LaTeX string
    clean_latex = sumen_processor.tokenizer.batch_decode(outputs.sequences)[0]
    
    # Remove special tokens from the output and return the cleaned LaTeX string
    return clean_latex.replace("<s>", "").replace("</s>", "").strip()