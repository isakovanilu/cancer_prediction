# SageMaker Model Deployment Automation

This project automates the deployment of a SageMaker machine learning model using AWS services like Lambda, EventBridge, S3, and IAM. The automation involves deploying a model after approval in SageMaker Model Registry and triggers a GitHub Actions workflow to continue the pipeline.

## Infrastructure Overview

The infrastructure is defined using Terraform and automates the following components:

1. **S3 Bucket**: Stores the model artifacts that will be deployed to SageMaker.
2. **IAM Roles and Policies**: Several roles are created to allow EventBridge and Lambda to perform actions such as invoking functions and interacting with SageMaker, S3, and GitHub.
3. **Lambda Functions**: 
   - **Model Deployment Lambda**: Deploys the approved SageMaker model.
   - **GitHub Trigger Lambda**: Triggers the GitHub Actions pipeline to continue the workflow after model deployment.
4. **EventBridge Rule**: Monitors SageMaker model approval events and triggers the deployment Lambda.
5. **CloudWatch Event Targets**: EventBridge invokes the deployment Lambda on a model approval event.
6. **GitHub Actions Workflow**: After model deployment, the GitHub workflow is triggered to handle further steps such as testing or post-deployment tasks.

## Project Components

### 1. S3 Bucket

The S3 bucket is used to store the model artifacts (trained models) before they are deployed to SageMaker.

- **Bucket Name**: `${{var.project_name}}-model-artifacts`
- **Bucket ACL**: `private`

### 2. IAM Roles & Policies

- **EventBridge Lambda Role**: Grants EventBridge permission to trigger the Lambda functions.
- **Lambda Execution Role**: Provides Lambda functions permission to interact with SageMaker, S3, and other AWS services.

### 3. Lambda Functions

- **Model Deployment Lambda**: Automatically deploys the SageMaker model once the model package is approved in the SageMaker Model Registry.
- **GitHub Trigger Lambda**: Triggers a GitHub Actions workflow after the model deployment is successful.

### 4. EventBridge Rule

EventBridge monitors the SageMaker model package for an "Approved" status and triggers the Model Deployment Lambda once this condition is met.

- **Rule Name**: `${{var.project_name}}_ModelApprovalRule`

### 5. GitHub Actions Integration

This project includes a GitHub Actions workflow that is triggered by the Lambda function after the SageMaker model is deployed. You will need to store your GitHub personal access token in AWS Secrets Manager for secure access.

## Requirements

To deploy this infrastructure, you will need:

- AWS CLI configured with appropriate credentials.
- Terraform installed on your local machine.
- An AWS account with access to S3, Lambda, EventBridge, and SageMaker services.
- A GitHub repository containing your workflow (`sagemaker_pipeline.yml`) CI part
- A valid GitHub personal access token stored in AWS Secrets Manager under the name `GitHubAccessToken`.

## Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone https://github.com/isakovanilu/sagemaker_cancer_prediction.git
   cd sagemaker_cancer_prediction
   
2. **Install Terraform**: Ensure that Terraform is installed on your machine. You can follow the official installation guide [here](https://developer.hashicorp.com/terraform/install)

3. **Initialize Terraform**:
   ```bash
   terraform init

4. **Set your AWS credentials**:
    ```bash
    export AWS_ACCESS_KEY_ID=<your-access-key>
    export AWS_SECRET_ACCESS_KEY=<your-secret-key>
5. **Deploy the Infrastructure**:
   ```bash
   terraform apply
6. **Trigger GitHub Actions Manually**: After deployment, you can trigger the GitHub Actions manually through the URL:
   ```ruby
   https://github.com/isakovanilu/sagemaker_cancer_prediction/actions

## Outputs
* GitHub Actions URL: The URL to trigger the GitHub Actions workflow for your SageMaker model pipeline

## Notes
* Ensure that the Lambda zip files (deployment-lambda.zip, github-trigger-lambda.zip) are uploaded to the specified S3 bucket (mysagemakerprojects in this case) before deployment.
* The GitHub personal access token needs appropriate scopes to trigger workflows. Ensure it has access to the repo and workflow scopes.







