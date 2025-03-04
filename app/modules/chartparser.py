import torch
from transformers import DonutProcessor, VisionEncoderDecoderModel, AutoProcessor
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def load_UniChart():
  """
  Loads the UniChart model.

  Paramaters:
  None

  Returns:
  model: The UniChart model.
  processor: The UniChart processor.
  """
  # Load UniChart model
  print("Loading UniChart model...")
  global unichart_model, unichart_processor
  unichart_model = VisionEncoderDecoderModel.from_pretrained("ahmed-masry/unichart-base-960").to(device)
  unichart_processor = DonutProcessor.from_pretrained("ahmed-masry/unichart-base-960")
  print("UniChart model loaded successfully!")
  return unichart_model, unichart_processor

def generate_unichart_response(image, prompt):
    """
    Generates a response using the UniChart model.

    Paramaters:
    image: The image to be processed.
    prompt: The prompt to be used for processing.

    Returns:
    response: The response from the UniChart model.
    """
    pixel_values = unichart_processor(image, return_tensors="pt").pixel_values.to(device)
    decoder_input_ids = unichart_processor.tokenizer(prompt, add_special_tokens=False, return_tensors="pt").input_ids
    outputs = unichart_model.generate(
        pixel_values,
        decoder_input_ids=decoder_input_ids.to(device),
        max_length=unichart_model.decoder.config.max_position_embeddings,
        early_stopping=True,
        pad_token_id=unichart_processor.tokenizer.pad_token_id,
        eos_token_id=unichart_processor.tokenizer.eos_token_id,
        use_cache=True,
        num_beams=4,
        bad_words_ids=[[unichart_processor.tokenizer.unk_token_id]],
        return_dict_in_generate=True,
    )
    response = unichart_processor.batch_decode(outputs.sequences)[0]
    response = response.replace(unichart_processor.tokenizer.eos_token, "").replace(unichart_processor.tokenizer.pad_token, "").strip()
    return response.split("<s_answer>")[1].strip() if "<s_answer>" in response else response

def parse_table_data(table_data):
    """
    Parses the table data returned from the chart model.

    Paramaters:
    table_data: The table data to be parsed.

    Returns:
    parsed_data: The parsed table data.
    """
    rows = table_data.split("&")
    headers = rows[0].split("|")
    parsed_data = []
    try:
      for row in rows[1:]:
          values = row.split("|")
          parsed_data.append({headers[i].strip(): values[i].strip() for i in range(len(headers))})
    except:
      parsed_data = []
    return parsed_data