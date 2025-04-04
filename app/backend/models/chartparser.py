import torch
from transformers import DonutProcessor, VisionEncoderDecoderModel
import re
from collections import Counter

# Determine the computation device: use GPU (CUDA) if available; otherwise, default to CPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def load_UniChart():
    """
    Load the UniChart model and processor.

    UniChart is a vision-language model specialized for chart comprehension.
    This function initializes the pre-trained model and processor.

    Returns:
        model (VisionEncoderDecoderModel): Pre-trained UniChart model.
        processor (DonutProcessor): Processor responsible for image preprocessing and text tokenization.
    """

    # Inform the user that the model is being loaded
    print("\n\n#-------------------- # Loading UniChart model # -------------------#\n")
    
    # Load the pre-trained UniChart model and assign it to the appropriate device
    global unichart_model, unichart_processor  # Declare global variables for model persistence
    unichart_model = VisionEncoderDecoderModel.from_pretrained("ahmed-masry/unichart-base-960").to(device)
    
    # Load the corresponding processor for image and text handling
    unichart_processor = DonutProcessor.from_pretrained("ahmed-masry/unichart-base-960")
    # Confirm successful model and processor loading
    print("\n----> UniChart model loaded successfully!")

    return unichart_model, unichart_processor  # Return the loaded model and processor

def is_hallucinated(response, repetition_threshold=20):
    """
    Detects hallucinated responses by identifying excessive word repetition.

    Parameters:
        response (str): The generated text response.
        repetition_threshold (int): Maximum allowable repetitions of any single word.

    Returns:
        (bool): True if the response is considered unreliable, False otherwise.
    """

    # Convert response to lowercase and tokenize it into words
    words = response.lower().split()

    # Count occurrences of each word
    word_counts = Counter(words)
    
    # Check if any word appears more times than the specified threshold
    return any(count > repetition_threshold for count in word_counts.values())

def generate_unichart_response(image, prompt):
    """
    Generates a response using the UniChart model based on an input image and text prompt.

    This function processes an input image, tokenizes the text prompt, and generates
    a structured response using beam search decoding.

    Parameters:
    image (PIL.Image or tensor): Input image of a chart or table.
    prompt (str): Text prompt describing the task or expected output.

    Returns:
    response (str): The generated response, post-processed to remove special tokens.
    If hallucination is detected, returns "Unreliable response".
    """

    # Convert the input image into pixel values compatible with the model
    pixel_values = unichart_processor(image, return_tensors="pt").pixel_values.to(device)
    
    # Tokenize the input prompt for the model's decoder
    decoder_input_ids = unichart_processor.tokenizer(prompt, add_special_tokens=False, return_tensors="pt").input_ids
    
    # Generate a response using beam search
    outputs = unichart_model.generate(
        pixel_values,  # Processed image input
        decoder_input_ids=decoder_input_ids.to(device),  
        max_length=unichart_model.decoder.config.max_position_embeddings,  
        early_stopping=True,  
        pad_token_id=unichart_processor.tokenizer.pad_token_id,  
        eos_token_id=unichart_processor.tokenizer.eos_token_id,
        use_cache=True,
        num_beams=4,  # Use beam search with 4 beams for better decoding accuracy
        bad_words_ids=[[unichart_processor.tokenizer.unk_token_id]],  # Prevent unknown tokens from appearing
        return_dict_in_generate=True,  # Return structured output
    )

    # Decode the generated sequence into a human-readable response
    response = unichart_processor.batch_decode(outputs.sequences)[0]

    # Remove special tokens from the output
    response = response.replace(unichart_processor.tokenizer.eos_token, "").replace(unichart_processor.tokenizer.pad_token, "").strip()
    
    # Extract only the answer portion if applicable
    response = response.split("<s_answer>")[1].strip() if "<s_answer>" in response else response

    # Debugging output (optional)
    # print(f"Generated response: {response}")

    # Apply hallucination filter before returning
    if is_hallucinated(response):
        return "Unreliable response"
    
    return response

def parse_table_data(table_data):
    """
    Parses structured table data extracted from a chart.

    This function converts a raw table output string into a structured list of dictionaries,
    where each dictionary represents a row with column headers as keys.

    Parameters:
    table_data (str): Raw table data in a structured text format (e.g., row values separated by "&", columns by "|").

    Returns:
    parsed_data (list[dict]): List of dictionaries representing structured table data.
    Returns an empty list if parsing fails.
    """

    # Split the raw table data into rows
    rows = table_data.split("&")
    headers = rows[0].split("|")
    parsed_data = []
    
    try:
        # Iterate through each row (excluding the header row) and create structured dictionary entries
        for row in rows[1:]:
            values = row.split("|")
            parsed_data.append({headers[i].strip(): values[i].strip() for i in range(len(headers))})
    
    # Handle potential parsing errors
    except Exception as e:
        print(f"Error parsing table: {e}")
        parsed_data = []

    return parsed_data # Return the structured table data