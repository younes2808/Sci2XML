# SmallLaTeXFormulaOCR

This small dataset consists of images of mathematical formulas and their corresponding LaTeX representations in text format. The dataset is intended to evaluate different LaTeX OCR (Optical Character Recognition) tools.

## Dataset Description

The dataset contains images of LaTeX formulas and their corresponding LaTeX code as text. It is a subset of the larger LaTeX_OCR dataset, which is available on Hugging Face [here](https://huggingface.co/datasets/linxy/LaTeX_OCR/viewer/default/train?p=4).

## Purpose

This dataset can be used to benchmark or test LaTeX OCR models and tools, particularly for recognizing and converting mathematical formulas from images back into LaTeX format.

## Acknowledgments

This dataset is a small part of the original [LaTeX_OCR](https://huggingface.co/datasets/linxy/LaTeX_OCR/viewer/default/train?p=4) dataset. All credits for the larger dataset go to the creators and contributors of LaTeX_OCR.

## Evaluation

Evaluation will be done on Google Colab(T4 GPU). Results and Code can be found in the Evaluation folder. 
The following LaTeX OCR Models will be evaluated:
- [X] LaTeXOCR [Github](https://github.com/lukas-blecher/LaTeX-OCR)
- [X] Sumen [Github](https://github.com/hoang-quoc-trung/sumen)
- [X] RapidLaTeXOCR [Github](https://github.com/RapidAI/RapidLaTeXOCR)
- [X] Nougat-LaTeX-OCR [Github](https://github.com/NormXU/nougat-latex-ocr) 
- [X] MixTex [Github](https://github.com/RQLuo/MixTeX-Latex-OCR?tab=readme-ov-file)
## Results

![data2](https://github.com/user-attachments/assets/8c814f90-976d-42b4-bca6-5d2df3b47ab3)
![DATA](https://github.com/user-attachments/assets/68b4cbc7-82bb-4375-ab39-df0b4ea66992)
