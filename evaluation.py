%%writefile evaluation.py

import os
import json
import tarfile
import logging
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score, classification_report


logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


if __name__ == "__main__":
    # Load the model
    logger.debug("Starting evaluation.")
    with tarfile.open("/opt/ml/processing/model/model.tar.gz") as tar:
        tar.extractall(path="/opt/ml/processing/model")
    model_path = os.path.join("/opt/ml/processing/model", "xgboost-model")
    model = xgb.Booster()
    
    logger.debug("Loading xgboost model.")
    model.load_model(model_path)
    
    logger.debug("Reading validation data")
    # Load the test data
    validation_data = pd.read_csv('/opt/ml/processing/output/validation/validation.csv')
    
    # Separate labels and features
    y_val = validation_data.iloc[:, 0].values  # First column is the label
    X_val = validation_data.iloc[:, 1:].values  # Remaining columns are the features

    # Perform inference
    dtest = xgb.DMatrix(X_val)
    
    logger.info("Performing predictions against validation data.")
    predictions = model.predict(dtest)
    predictions_binary = [1 if pred > 0.5 else 0 for pred in predictions]

    # Evaluate the model
    accuracy = accuracy_score(y_val, predictions_binary)
    report = classification_report(y_val, predictions_binary, output_dict=True)
    
    # Define the output directory and file path
    evaluation_output_dir = "/opt/ml/processing/output/evaluation/"
    evaluation_output_path = os.path.join(evaluation_output_dir, "evaluation.json")

    # Ensure the output directory exists
    os.makedirs(evaluation_output_dir, exist_ok=True)
    
    # Save the evaluation results
    logger.info("Writing out evaluation report")
    with open(evaluation_output_path, "w") as f:
        json.dump({"accuracy": accuracy, "report": report}, f)
