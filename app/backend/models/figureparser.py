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
        model (torch.nn.Module or None): The pre-trained Moondream2 model, or None if loading failed.
        tokenizer (transformers.PreTrainedTokenizer or None): Tokenizer corresponding to Moondream2, or None if loading failed.
    """

    print("\n#-------------------- # Loading Moondream2 model # -----------------#\n")

    try:
        # Load the model
        model = AutoModelForCausalLM.from_pretrained(
            "vikhyatk/moondream2",
            revision="2025-01-09",
            trust_remote_code=True,
            device_map={"": "cuda" if torch.cuda.is_available() else "cpu"}
        ).eval()  # Set model to eval mode

        # Load the tokenizer
        tokenizer = AutoTokenizer.from_pretrained("vikhyatk/moondream2", trust_remote_code=True)

        print("\n----> Moondream2 model loaded successfully!\n")
        return model, tokenizer

    except Exception as e:
        print(f"\n[ERROR] Failed to load Moondream2 model or tokenizer: {e}")
        return None, None
