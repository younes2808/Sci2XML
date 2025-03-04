
import torch
from PIL import Image
from transformers import AutoModelForCausalLM, AutoTokenizer
from io import BytesIO


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def load():
  # Load Moondream2 model
  print("Loading Moondream2 model...")
  model = AutoModelForCausalLM.from_pretrained(
      "vikhyatk/moondream2",
      revision="2025-01-09",
      trust_remote_code=True,
      device_map={"": "cuda" if torch.cuda.is_available() else "cpu"}
  ).eval()

  tokenizer = AutoTokenizer.from_pretrained("vikhyatk/moondream2", trust_remote_code=True)
  print("Moondream2 model loaded successfully!")

  return model, tokenizer
