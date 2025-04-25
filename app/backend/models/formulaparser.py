import torch
from transformers import DonutProcessor, VisionEncoderDecoderModel, AutoProcessor

# Determine the computation device: use GPU (CUDA) if available; otherwise, default to CPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def load_sumen():
    """
    Load the Sumen model and processor.

    Sumen is an OCR (Optical Character Recognition) model optimized for document understanding tasks.
    This function loads the pre-trained model and the associated processor for handling image inputs.

    Returns:
        model (VisionEncoderDecoderModel): Pre-trained Sumen OCR model.
        processor (AutoProcessor): Processor for image preprocessing and text tokenization.
    """
    print("\n#-------------------- # Loading Sumen OCR model # ------------------#\n")

    try:
        global sumen_model, sumen_processor  # Declare global variables for model persistence

        # Load the model and move it to the appropriate device
        sumen_model = VisionEncoderDecoderModel.from_pretrained("hoang-quoc-trung/sumen-base").to(device)
        sumen_processor = AutoProcessor.from_pretrained("hoang-quoc-trung/sumen-base")

        print("\n----> Sumen model loaded successfully!")
        return sumen_model, sumen_processor

    except Exception as e:
        print(f"\n[ERROR] Failed to load Sumen model or processor: {e}")
        return None, None

def run_sumen_ocr(image):
    """
    Perform OCR using the Sumen model on a given image.

    Parameters:
    image (PIL.Image or tensor): Input image to be processed by the OCR model.

    Returns:
    clean_latex (str): The extracted text in LaTeX format, with unnecessary tokens removed.    
    """
    try:
        if sumen_model is None or sumen_processor is None:
            raise RuntimeError("Sumen model and processor are not loaded. Please call load_sumen() first.")

        # Preprocess the image
        pixel_values = sumen_processor.image_processor(image, return_tensors="pt").pixel_values.to(device)

        task_prompt = sumen_processor.tokenizer.bos_token
        decoder_input_ids = sumen_processor.tokenizer(task_prompt, add_special_tokens=False, return_tensors="pt").input_ids

        with torch.no_grad():
            outputs = sumen_model.generate(
                pixel_values,
                decoder_input_ids=decoder_input_ids.to(device),
                max_length=sumen_model.decoder.config.max_length,
                pad_token_id=sumen_processor.tokenizer.pad_token_id,
                eos_token_id=sumen_processor.tokenizer.eos_token_id,
                use_cache=True,
                num_beams=4,
                bad_words_ids=[[sumen_processor.tokenizer.unk_token_id]],
                return_dict_in_generate=True,
            )

        clean_latex = sumen_processor.tokenizer.batch_decode(outputs.sequences)[0]
        return clean_latex.replace("<s>", "").replace("</s>", "").strip()

    except Exception as e:
        print(f"\n[ERROR] OCR failed: {e}")
        return ""
