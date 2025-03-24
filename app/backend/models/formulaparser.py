import torch
from transformers import DonutProcessor, VisionEncoderDecoderModel, AutoProcessor

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def load_Sumen():
  
  """
  Loads the Sumen model.

  Paramaters:
  None

  Returns:
  model: The Sumen model.
  processor: The Sumen processor.
  """
  # Load Sumen model
  print("\n\n#-------------------- # Loading Sumen OCR model # ------------------#\n")
  global sumen_model, sumen_processor
  sumen_model = VisionEncoderDecoderModel.from_pretrained("hoang-quoc-trung/sumen-base").to(device)
  sumen_processor = AutoProcessor.from_pretrained("hoang-quoc-trung/sumen-base")
  print("----->Sumen model loaded successfully!")
  return sumen_model, sumen_processor

def run_sumen_ocr(image):
    with open("formulaparserrun.txt", "a") as file:
        file.write("\n run now")
    """
    Runs the Sumen OCR model on the given image.

    Paramaters:
    image: The image to be processed.

    Returns:
    clean_latex: The processed LaTeX code.
    """
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