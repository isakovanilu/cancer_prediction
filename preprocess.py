
import os
import boto3
import argparse
import sagemaker
import pandas as pd

from sagemaker import get_execution_role
from sklearn.preprocessing import OneHotEncoder

# split data into train and test
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

def preprocessing_data(input_data_dir):
    
    bucket = input_data_dir.split('/')[2]
    prefix = "ll-ml-model"
    
    # SageMaker session
    sagemaker_session = sagemaker.Session()
    input_data = pd.read_csv(input_data_dir)
    df = input_data.copy()

    # Encode categorical features
    le_gender = LabelEncoder()
    le_cancer_type = LabelEncoder()
    df['outcome'] = df['outcome'].apply(lambda x: 1 if x == 'survived' else 0)
    df['gender'] = le_gender.fit_transform(df['gender'])
    df['cancer_type'] = le_cancer_type.fit_transform(df['cancer_type'])
    
    # Separate features and labels
    X = df.drop('outcome', axis=1)
    y = df['outcome']
    
    # Scale the numerical features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Split the data into training and test sets
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42, stratify=y)
    
    # Convert to CSV format and save locally
    # Ensure the label is the first column in the dataset
    train_data = pd.concat([y_train.reset_index(drop=True), pd.DataFrame(X_train)], axis=1)
    test_data = pd.concat([y_test.reset_index(drop=True), pd.DataFrame(X_test)], axis=1)
    
    # Save the datasets as CSV files without headers
    train_data.to_csv('train.csv', index=False, header=False)
    test_data.to_csv('validation.csv', index=False, header=False)



    # Upload the data to S3
    train_data_s3_path = sagemaker_session.upload_data(path='train.csv', bucket=bucket, key_prefix=f"{prefix}/train")
    print('Saved Train data', train_data_s3_path)
    test_data_s3_path = sagemaker_session.upload_data(path='validation.csv', bucket=bucket, key_prefix=f"{prefix}/validation")
    print('Saved Test data', test_data_s3_path)
    
    

    return train_data_s3_path, test_data_s3_path

    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('input_data_dir')
    args = parser.parse_args()
    preprocessing_data(args.input_data_dir)





