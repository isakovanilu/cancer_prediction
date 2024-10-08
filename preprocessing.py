
import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

# Define input and output paths based on environment variables
input_data_path = os.path.join('/opt/ml/processing/input', 'test-data.csv')  # S3 input gets mounted here
# output_dir = '/opt/ml/processing/output/'  # Define the output directory
# output_train_path = os.path.join(output_dir, 'train.csv')
# output_validation_path = os.path.join(output_dir, 'validation.csv')

output_train_path = os.path.join('/opt/ml/processing/output/train', 'train.csv')
output_validation_path = os.path.join('/opt/ml/processing/output/validation', 'validation.csv')

def preprocess_data(data):
    # Drop rows with missing values
    data = data.dropna()        
        
    # Encode categorical features
    le_gender = LabelEncoder()
    le_cancer_type = LabelEncoder()
    data['outcome'] = data['outcome'].apply(lambda x: 1 if x == 'survived' else 0)
    data['gender'] = le_gender.fit_transform(data['gender'])
    data['cancer_type'] = le_cancer_type.fit_transform(data['cancer_type'])
    
    

    # Split data into features and labels if needed
    if 'outcome' in data.columns:
        X = data.drop('outcome', axis=1)
        y = data['outcome']
    else:
        X, y = data, None

    return X, y

if __name__ == "__main__":
    # Load the dataset
    print("Reading input data from:", input_data_path)
    data = pd.read_csv(input_data_path)

    # Preprocess the data
    print("Preprocessing data...")
    X, y = preprocess_data(data)
    
    # Scale the numerical features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Split the data into training and test sets
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42, stratify=y)
    
    # os.makedirs(output_dir, exist_ok=True)
    # Convert to CSV format and save locally
    # Ensure the label is the first column in the dataset
    train_data = pd.concat([y_train.reset_index(drop=True), pd.DataFrame(X_train)], axis=1)
    print('train_data', train_data.head(2))
    validation_data = pd.concat([y_test.reset_index(drop=True), pd.DataFrame(X_test)], axis=1)
    print('validation_data', validation_data.head(2))
    
    print("Saving train and validation data", output_train_path, ' + ', output_validation_path)

    # Save the datasets as CSV files without headers
    train_data.to_csv(output_train_path, index=False, header=False)
    validation_data.to_csv(output_validation_path, index=False, header=False)


