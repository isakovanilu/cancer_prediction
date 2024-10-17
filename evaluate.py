import os
import json
import pandas as pd
from sagemaker.serializers import CSVSerializer
from sagemaker.deserializers import JSONDeserializer
from sagemaker.predictor import Predictor
from sklearn.metrics import classification_report, accuracy_score

# Path to validation data
validation_data_path = "/opt/ml/processing/output/validation/validation.csv"

# Load validation data
validation_data = pd.read_csv(validation_data_path)

# Separate features and target
X_val = validation_data.iloc[:, 1:]  # All columns except first are features
y_val = validation_data.iloc[:, 0]   # First column is target

# Define the endpoint name for your model
# Make sure you have a deployed model in SageMaker and update the endpoint name
endpoint_name = "linear-learner-endpoint"

# Set up the SageMaker Predictor
predictor = Predictor(
    endpoint_name=endpoint_name,
    serializer=CSVSerializer(),       # Serialize input data in CSV format
    deserializer=JSONDeserializer(),  # Deserialize output from JSON
)

# Prepare data for prediction
X_val_csv = X_val.to_csv(header=False, index=False).encode("utf-8")

# Perform inference (predictions)
predictions = predictor.predict(X_val_csv)

# Extract predicted labels
predicted_labels = [float(pred['predicted_label']) for pred in predictions['predictions']]

# Evaluate the predictions against the actual labels
accuracy = accuracy_score(y_val, predicted_labels)
report = classification_report(y_val, predicted_labels, output_dict=True)

# Save the evaluation results
evaluation_output_dir = "/opt/ml/processing/evaluation"
os.makedirs(evaluation_output_dir, exist_ok=True)

# Save accuracy score
accuracy_report = {"accuracy": accuracy}
with open(os.path.join(evaluation_output_dir, "accuracy.json"), "w") as f:
    json.dump(accuracy_report, f)

# Save detailed classification report
with open(os.path.join(evaluation_output_dir, "classification_report.json"), "w") as f:
    json.dump(report, f)

print("Evaluation complete. Results saved to:", evaluation_output_dir)
