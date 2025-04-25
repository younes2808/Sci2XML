# Training the DenseNet-169 ML classification model

The training of the model was done by following the training pipeline in this notebook on [Kaggle](https://www.kaggle.com/code/sunedition/classification-of-graphs). The code was adapted for our use case and we added another category to the classes.

## Dataset

The dataset used was also from [Kaggle](https://www.kaggle.com/datasets/sunedition/graphs-dataset?resource=download), and consists of 8 categories: 15875 samples of images of graphs divided into 8 classes: just image - bar chart - diagram - flow chart - graph - growth chart - pie chart - table. We expanded on the dataset by adding a ninth category of text_sentences.

To create the images for the text_sentences category we used a tool called [TextRecognitionDataGenerator](https://github.com/Belval/TextRecognitionDataGenerator) which creates images of text sentences of variying length. We generated 600 images with 15 words, 600 with 10 and 600 with 7 words. The command used was "trdg -c 600 -w 10 -f 64".