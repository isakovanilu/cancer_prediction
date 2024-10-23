provider "aws" {
  region = "us-east-1"
}

# S3 Bucket for storing model artifacts
resource "aws_s3_bucket" "model_artifacts" {
  bucket = "${var.project_name}-model-artifacts"
  acl    = "private"
}

# IAM role for EventBridge to trigger Lambda
resource "aws_iam_role" "eventbridge_lambda_role" {
  name = "${var.project_name}_eventbridge_lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement: [
      {
        Effect    = "Allow",
        Principal = {
          Service = "events.amazonaws.com"
        },
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

# IAM policy to allow EventBridge to trigger Lambda
resource "aws_iam_role_policy" "eventbridge_lambda_policy" {
  name = "${var.project_name}_eventbridge_lambda_policy"
  role = aws_iam_role.eventbridge_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement: [
      {
        Effect: "Allow",
        Action: [
          "lambda:InvokeFunction"
        ],
        Resource: "*"
      }
    ]
  })
}

# Lambda IAM Role
resource "aws_iam_role" "lambda_exec_role" {
  name = "${var.project_name}_lambda_exec_role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action    = "sts:AssumeRole",
        Effect    = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Update the Lambda IAM Role to allow invoking other Lambda functions
resource "aws_iam_role_policy" "lambda_policy" {
  name   = "${var.project_name}_lambda_policy"
  role   = aws_iam_role.lambda_exec_role.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "sagemaker:*",
          "s3:*",
          "logs:*",
          "lambda:InvokeFunction",
          "iam:PassRole"
        ],
        Resource = [
          "*",
          aws_lambda_function.github_trigger_lambda.arn,
        "arn:aws:iam::390403890405:role/sagemaker-user-example"
        ]
      }
    ]
  })
}

# Lambda Function to deploy the SageMaker model after approval
resource "aws_lambda_function" "model_deployment_lambda" {
  function_name = "${var.project_name}_ModelDeploymentLambda"
  handler       = "lambda_function.lambda_handler"
  role          = aws_iam_role.lambda_exec_role.arn
  runtime       = "python3.8"
  s3_bucket     = "mysagemakerprojects"  
  s3_key        = "deployment-lambda.zip"  
}

# Lambda Function to trigger GitHub Actions
resource "aws_lambda_function" "github_trigger_lambda" {
  function_name = "${var.project_name}_GitHubTriggerLambda"
  handler       = "lambda_function.lambda_handler"
  role          = aws_iam_role.lambda_exec_role.arn
  runtime       = "python3.8"
  s3_bucket     = "mysagemakerprojects"
  s3_key        = "github-trigger-lambda.zip"
  environment {
    variables = {
      GITHUB_REPO_OWNER  = "isakovanilu"
      GITHUB_REPO_NAME   = "sagemaker_cancer_prediction"
      GITHUB_WORKFLOW    = "sagemaker_pipeline.yml"
    }
  }
}

# SageMaker Model Package Group (Model Registry)
resource "aws_sagemaker_model_package_group" "model_package_group" {
  model_package_group_name        = "PipelineModelPackageGroup"
  model_package_group_description = "Group for all versions of my machine learning model"
}

# Retrieve GitHub token from AWS Secrets Manager
data "aws_secretsmanager_secret" "github_token" {
  name = "GitHubAccessToken"
}

data "aws_secretsmanager_secret_version" "github_token_value" {
  secret_id = data.aws_secretsmanager_secret.github_token.id
}

# EventBridge rule to trigger the Lambda when model package is approved
resource "aws_cloudwatch_event_rule" "model_approval_rule" {
  name        = "${var.project_name}_ModelApprovalRule"
  description = "Trigger Lambda on SageMaker Model Package approval"
  event_pattern = jsonencode({
    "source"       : ["aws.sagemaker"],
    "detail-type"  : ["SageMaker Model Package State Change"],
    "detail"       : {
      "ModelPackageGroupName": [aws_sagemaker_model_package_group.model_package_group.model_package_group_name],
      "CurrentStatus"        : ["Approved"]
    }
  })
}

# EventBridge Target to trigger the first Lambda function
resource "aws_cloudwatch_event_target" "deployment_lambda_target" {
  rule      = aws_cloudwatch_event_rule.model_approval_rule.name
  target_id = "TriggerModelDeploymentLambda"
  arn       = aws_lambda_function.model_deployment_lambda.arn
}

# Permission for EventBridge to invoke the first Lambda
resource "aws_lambda_permission" "allow_eventbridge_to_invoke_deployment_lambda" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.model_deployment_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.model_approval_rule.arn
}

# Lambda trigger for the second Lambda function after the first one succeeds
resource "aws_lambda_permission" "allow_deployment_lambda_to_invoke_github_lambda" {
  statement_id  = "AllowDeploymentLambdaToInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.github_trigger_lambda.function_name
  principal     = "lambda.amazonaws.com"
}

# Invoke the second Lambda after the first completes (through function chaining)
resource "aws_lambda_function_event_invoke_config" "deployment_to_github_trigger" {
  function_name = aws_lambda_function.model_deployment_lambda.function_name

  destination_config {
    on_success {
      destination = aws_lambda_function.github_trigger_lambda.arn
    }
  }
}

# GitHub Actions URL for manual trigger (optional)
output "github_actions_url" {
  value       = "https://github.com/isakovanilu/sagemaker_cancer_prediction/actions"
  description = "GitHub Actions workflow URL to trigger the pipeline."
}

variable "project_name" {
  description = "Name of the project"
  default     = "sagemaker-cancer-prediction"
}
