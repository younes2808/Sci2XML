## Load-modules ##
from skorch import NeuralNetClassifier
import torch.nn as nn
import torch
import multiprocessing as mp
from skorch.dataset import ValidSplit
from skorch.callbacks import LRScheduler, Checkpoint
from skorch.callbacks import Freezer, EarlyStopping
import torchvision
from PIL import Image
import albumentations as A
import numpy as np

# This code is adapted from ---> https://www.kaggle.com/code/sunedition/classification-of-graphs <---

def loadML():
  """
  Load the ML model used for classification.

  Paramaters:
  None

  Returns:
  densenet: The ML model.
  """
  print("\n#-------------------- # Loading ML Classifier # --------------------#\n")

  n_classes = 9
  batch_size = 128
  num_workers = mp.cpu_count()

  # callback functions for models

  # DenseNet169
  # callback for Reduce on Plateau scheduler
  lr_scheduler = LRScheduler(policy='ReduceLROnPlateau',
                                      factor=0.5, patience=1)
  # callback for saving the best on validation accuracy model
  checkpoint = Checkpoint(f_params='best_model_densenet169.pkl',
                                  monitor='valid_acc_best')
  # callback for freezing all layer of the model except the last layer
  freezer = Freezer(lambda x: not x.startswith('model.classifier'))
  # callback for early stopping
  early_stopping = EarlyStopping(patience=5)

  # ... (import other necessary libraries) ...
  class DenseNet169(nn.Module):
      def __init__(self, output_features, num_units=512, drop=0.5,
                  num_units1=512, drop1=0.5):
          super().__init__()
          model = torchvision.models.densenet169(pretrained=True)
          n_inputs = model.classifier.in_features
          model.classifier = nn.Sequential(
                                  nn.Linear(n_inputs, num_units),
                                  nn.ReLU(),
                                  nn.Dropout(p=drop),
                                  nn.Linear(num_units, num_units1),
                                  nn.ReLU(),
                                  nn.Dropout(p=drop1),
                                  nn.Linear(num_units1, output_features))
          self.model = model

      def forward(self, x):
          return self.model(x)
  # NeuralNetClassifier for based on DenseNet169 with custom parameters
  densenet = NeuralNetClassifier(
      # pretrained DenseNet169 + custom classifier
      module=DenseNet169,
      module__output_features=n_classes,
      # criterion
      criterion=nn.CrossEntropyLoss,
      # batch_size = 128
      batch_size=batch_size,
      # number of epochs to train
      max_epochs=5,
      # optimizer Adam used
      optimizer=torch.optim.Adam,
      optimizer__lr = 0.001,
      optimizer__weight_decay=1e-6,
      # shuffle dataset while loading
      iterator_train__shuffle=True,
      # load in parallel
      iterator_train__num_workers=num_workers,
      # stratified kfold split of loaded dataset
      train_split=ValidSplit(cv=5, stratified=True),
      # callbacks declared earlier
      callbacks=[lr_scheduler, checkpoint, freezer, early_stopping],
      # use GPU or CPU
      device="cuda:0" if torch.cuda.is_available() else "cpu"
  )

  densenet.initialize()  # Initialize the model before loading parameters
  densenet.load_params(f_params='Sci2XML/app/backend/models/best_model_densenet169_sentence.pkl')
  # Load the saved model
  global ML
  ML = densenet
  print("\n----> ML classifier model loaded successfully")
  return densenet

def callML(model, image):
  """
  Calls the ML model that will classify the image.

  Paramaters:
  model: The ML model.
  image: The image to be classified.

  Returns:
  predicted_class_name: The name of the predicted class.
  """

  # Load the image
  image = image.convert("RGB")  # Ensure the image is in RGB format

  img_size = 224

  # Define the same transformations used during training
  data_transforms = A.Compose([
      A.Resize(img_size, img_size),
      A.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
      A.pytorch.transforms.ToTensorV2()
  ])

  # Apply transformations
  transformed_image = data_transforms(image=np.array(image))["image"]

  # Add a batch dimension
  transformed_image = transformed_image.unsqueeze(0)

  # Move the image to the appropriate device (GPU or CPU)
  device = "cuda:0" if torch.cuda.is_available() else "cpu"
  transformed_image = transformed_image.to(device)

  # Make prediction
  predicted_class = model.predict(transformed_image)

  # Get the class name
  class_names = ['just_image', 'bar_chart', 'diagram', 'flow_chart', 'graph',
                'growth_chart', 'pie_chart', 'table', 'text_sentence']
  predicted_class_name = class_names[predicted_class[0]]

  return predicted_class_name