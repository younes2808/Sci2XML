import torch
from PIL import Image
from transformers import AutoModelForCausalLM, AutoTokenizer
from io import BytesIO

# Determine the device to use: CUDA (GPU) if available, otherwise CPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def load():
  """
  Load the Moondream2 model and tokenizer.

  Moondream2 is a vision-language model designed for multimodal tasks.
  
  Returns:
  model (torch.nn.Module): The pre-trained Moondream2 model.
  tokenizer (transformers.PreTrainedTokenizer): Tokenizer corresponding to Moondream2.
  """

  # Inform the user that the model is being loaded
  print("\n\n#-------------------- # Loading Moondream2 model # -----------------#\n")

  # Load the Moondream2 model from the Hugging Face repository
  model = AutoModelForCausalLM.from_pretrained(
      "vikhyatk/moondream2",
      revision="2025-01-09",
      trust_remote_code=True,
      device_map={"": "cuda" if torch.cuda.is_available() else "cpu"}  # Assigns model to GPU if available
  ).eval()  # Set the model to evaluation mode (disables training-specific behavior)

  # Load the corresponding tokenizer
  tokenizer = AutoTokenizer.from_pretrained("vikhyatk/moondream2", trust_remote_code=True)

  # Confirm successful loading
  print("----> \n\nMoondream2 model loaded successfully!\n")

  return model, tokenizer  # Return both the model and tokenizer for use in inference