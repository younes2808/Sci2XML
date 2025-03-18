import torch
from transformers import DonutProcessor, VisionEncoderDecoderModel, AutoProcessor
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
import re

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


def is_hallucinated(response):
    """
    Checks if the response contains hallucinated patterns such as excessive repetition.
    
    Parameters:
    response (str): The model-generated response.

    Returns:
    bool: True if hallucination is detected, False otherwise.
    """
    words = response.split()
    
    # Check for excessive repetition (e.g., "Staten Staten Staten Staten")
    if len(words) > 50 and len(set(words)) < len(words) * 0.2:  # More than 80% repetition
        return True

    # Check for repeating phrases (e.g., "the United States" repeated multiple times)
    repeated_phrases = re.findall(r'(\b\w+(?:\s+\w+){1,3}\b)(?=.*\1)', response)
    if len(repeated_phrases) > 5:
        return True

    # Check for excessive character repetition (e.g., "1- 1- 1- 1- 1-")
    if re.search(r'(\b\w+\b)(?:\s+\1){5,}', response):  # Five or more repetitions
        return True

    return False

def check_numerical_sanity(response):
    """
    Ensures numerical data in the response follows reasonable patterns.
    """
    numbers = [float(n) for n in re.findall(r'\d+\.\d+|\d+', response)]  # Extract numbers
    if not numbers:
        return True  # No numbers, so it's not necessarily hallucinated

    mean_value = sum(numbers) / len(numbers)
    if any(n > mean_value * 10 or n < mean_value / 10 for n in numbers):  # Outliers
        return False
    
    return True

def generate_unichart_response(image, prompt):
    """
    Generates a response using the UniChart model.

    Parameters:
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
    response = response.split("<s_answer>")[1].strip() if "<s_answer>" in response else response

    # Apply hallucination filters before returning the response
    if is_hallucinated(response) or not check_numerical_sanity(response):
        return "Unreliable response"
    
    return response


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