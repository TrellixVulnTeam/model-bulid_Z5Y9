"""Evaluation script for measuring mean squared error."""
import os
import json
import subprocess
import sys
import numpy as np
import pandas as pd
import pathlib
import tarfile
import argparse
import logging
from sklearn.metrics import mean_squared_error

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def get_test_data(test_dir):
    test_df = pd.read_csv(os.path.join(f"{test_dir}/test_df.csv"))    
    print('test_df shape: ', test_df.shape)
    return test_df

def make_dataset(dataframe, is_train=True):
    batch_size = 64
    labels = tf.ragged.constant(dataframe["TAC_Closing_Summing_up"].values)
    label_binarized = lookup(labels).numpy()
    dataset = tf.data.Dataset.from_tensor_slices((dataframe["Fault Symptom"].values, label_binarized))
    dataset = dataset.shuffle(batch_size * 10) if is_train else dataset
    return dataset.batch(batch_size)


if __name__ == "__main__":
    
    print("Python version")
    print (sys.version)
    print("Version info.")
    print (sys.version_info)

    install("tensorflow==2.6.2")
    model_path = f"/opt/ml/processing/model/model.tar.gz"
    with tarfile.open(model_path, "r:gz") as tar:
        tar.extractall("./model")
        
        
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import optimizers

    
    train_dir = "/opt/ml/processing/train/"
    train_df = pd.read_csv(os.path.join(f"{train_dir}/train_df.csv"))    
    print('train_df shape: ', train_df.shape)
    
    
    test_dir = "/opt/ml/processing/test/"
    test_df = pd.read_csv(os.path.join(f"{test_dir}/test_df.csv"))    
    print('test_df shape: ', test_df.shape)
    
    
    
    
    terms = tf.ragged.constant(train_df["TAC_Closing_Summing_up"].values)
    print(terms)
    lookup =  tf.keras.layers.StringLookup(output_mode="one_hot")
    lookup.adapt(terms)
    vocab = lookup.get_vocabulary()
    print("Vocabulary:\n")
    print(vocab)
    vocab.sort()
    
    sample_label = train_df["TAC_Closing_Summing_up"].iloc[0]
    print(f"Original label: {sample_label}")

    label_binarized = lookup([sample_label])
    print(f"Label-binarized representation: {(label_binarized)}")    
    print(train_df.head(10))
    
    
    
    
    #Now we can prepare the tf.data.Dataset objects.
    train_dataset = make_dataset(train_df, is_train=True)
    test_dataset = make_dataset(test_df, is_train=False)
    
    
    #Dataset preview
    text_batch, label_batch = next(iter(train_dataset))
    
    for i, text in enumerate(text_batch[:5]):
        label = label_batch[i].numpy()[None, ...]
        print(f"Fault symptom describtion: {text}")
        print(f"TAC Closing Summing up(s): {invert_multi_hot(label[0])}")
        print(" ")

    
    
    #Vectorization
    # Source: https://stackoverflow.com/a/18937309/7636462
    #Before we feed the data to our model, we need to vectorize it (represent it in a numerical form).
    #For that purpose, we will use the TextVectorization layer.
    #It can operate as a part of your main model so that the model is excluded from the core preprocessing logic.
    #This greatly reduces the chances of training / serving skew during inference.

    #We first calculate the number of unique words present in the abstracts.

    vocabulary = set()
    train_df["Fault Symptom"].str.lower().str.split().apply(vocabulary.update)
    vocabulary_size = len(vocabulary)
    print(vocabulary_size)
    
    
    
    text_vectorizer = layers.TextVectorization(max_tokens=vocabulary_size, ngrams=2, output_mode="tf_idf")

    # `TextVectorization` layer needs to be adapted as per the vocabulary from our training set.
    with tf.device("/CPU:0"):
        text_vectorizer.adapt(train_dataset.map(lambda text, label: text))

    train_dataset = train_dataset.map(lambda text, label: (text_vectorizer(text), label), num_parallel_calls=auto).prefetch(auto)
    test_dataset = test_dataset.map(lambda text, label: (text_vectorizer(text), label), num_parallel_calls=auto).prefetch(auto)
    
    

    
    print("Loaded Model...")
    model_loded = tf.keras.models.load_model("./model/1")
    print(model_loded.summary())
    acc = model_loded.evaluate(test_dataset)
    print("Categorical accuracy: ", acc)
    
    
    
     # The metrics reported can change based on the model used, but it must be a specific name per (https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor-model-quality-metrics.html)
    report_dict = {
        "multiclass_classification_metrics": {
            "accuracy": {
                "value": acc,
                "standard_deviation": "NaN",
        },
     }
    }

    print("Classification report:\n{}".format(report_dict))
    
    
    output_dir = "/opt/ml/processing/evaluation"
    pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)

    logger.info("Writing out evaluation report with acc: %f", acc)
    evaluation_path = f"{output_dir}/evaluation.json"
    with open(evaluation_path, "w") as f:
        f.write(json.dumps(report_dict))

#     evaluation_output_path = os.path.join("/opt/ml/processing/evaluation", "evaluation.json")
#     print("Saving classification report to {}".format(evaluation_output_path))

#     with open(evaluation_output_path, "w") as f:
#         f.write(json.dumps(report_dict))
    
    
    
   
    

#     logger.info("Performing predictions against test data.")
#     predictions = model_loded.predict(x_test)
    
#     #print("predictions: ", predictions)

#     logger.debug("Calculating mean squared error.")
#     mse = mean_squared_error(y_test, predictions)
#     std = np.std(y_test - predictions)
    
    
#      # Available metrics to add to model: https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor-model-quality-metrics.html
#     report_dict = {
#         "regression_metrics": {
#             "mse": {
#                 "value": mse,
#                 "standard_deviation": "NaN"
#             }
#         }
#     }

#     output_dir = "/opt/ml/processing/evaluation"
#     pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)

#     logger.info("Writing out evaluation report with mse: %f", mse)
#     evaluation_path = f"{output_dir}/evaluation.json"
#     with open(evaluation_path, "w") as f:
#         f.write(json.dumps(report_dict))
#     #logger.info("Processing Stage Done!")
    