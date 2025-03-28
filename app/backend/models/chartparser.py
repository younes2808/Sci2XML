import torch
from transformers import DonutProcessor, VisionEncoderDecoderModel
import re
from collections import Counter

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def load_UniChart():
    """Loads the UniChart model."""
    print("\n\n#-------------------- # Loading UniChart model # -------------------#\n")
    global unichart_model, unichart_processor
    unichart_model = VisionEncoderDecoderModel.from_pretrained("ahmed-masry/unichart-base-960").to(device)
    unichart_processor = DonutProcessor.from_pretrained("ahmed-masry/unichart-base-960")
    print("----->UniChart model loaded successfully!")
    return unichart_model, unichart_processor

def is_hallucinated(response, repetition_threshold=20):
    """Detects excessive repetition in the response."""
    words = response.lower().split()
    word_counts = Counter(words)
    
    # Check if any word is repeated more than repetition_threshold times
    if any(count > repetition_threshold for count in word_counts.values()):
        return True

    return False

def generate_unichart_response(image, prompt):
    """Generates a response using the UniChart model."""
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

    # Debugging output
    # print(f"Generated response: {response}")

    # Apply hallucination filter before returning
    if is_hallucinated(response):
        # print("Response marked as unreliable")
        return "Unreliable response"
    
    return response

def parse_table_data(table_data):
    """Parses the table data returned from the chart model."""
    rows = table_data.split("&")
    headers = rows[0].split("|")
    parsed_data = []
    
    try:
        for row in rows[1:]:
            values = row.split("|")
            parsed_data.append({headers[i].strip(): values[i].strip() for i in range(len(headers))})
    except Exception as e:
        print(f"Error parsing table: {e}")
        parsed_data = []

    return parsed_data