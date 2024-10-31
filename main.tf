provider "aws" {
  region = "us-east-1"
}

variable "project_name" {
  description = "Name of the project"
  default     = "sagemaker-cancer-prediction"
}

# S3 Bucket for storing model artifacts
resource "aws_s3_bucket" "model_artifacts" {
  bucket = "${var.project_name}-model-artifacts"
  acl    = "private"
}

# Lambda Function for Cancer Prediction Model
resource "aws_lambda_function" "my_lambda" {
  function_name    = "cancer-pred-ml-model-lambda-prod"
  filename         = "lambda_gateway.zip"
  handler          = "lambda_gateway.lambda_handler"
  runtime          = "python3.11"
  role             = aws_iam_role.lambda_exec_role.arn
  memory_size      = 512
  timeout          = 10
}

# API Gateway Setup for Lambda Function
resource "aws_api_gateway_rest_api" "my_api" {
  name        = "ml-model-api"
  description = "API Gateway for my Lambda function"
}

resource "aws_api_gateway_resource" "my_resource" {
  rest_api_id = aws_api_gateway_rest_api.my_api.id
  parent_id   = aws_api_gateway_rest_api.my_api.root_resource_id
  path_part   = "api-ml-model"
}

resource "aws_api_gateway_method" "my_method" {
  rest_api_id   = aws_api_gateway_rest_api.my_api.id
  resource_id   = aws_api_gateway_resource.my_resource.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda_integration" {
  rest_api_id             = aws_api_gateway_rest_api.my_api.id
  resource_id             = aws_api_gateway_resource.my_resource.id
  http_method             = aws_api_gateway_method.my_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.my_lambda.invoke_arn
}

resource "aws_lambda_permission" "api_gateway_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.my_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.my_api.execution_arn}/*/*"
}

resource "aws_api_gateway_deployment" "my_deployment" {
  rest_api_id = aws_api_gateway_rest_api.my_api.id
  stage_name  = "prod"
  depends_on  = [aws_api_gateway_integration.lambda_integration]
}

# IAM Roles and Policies
resource "aws_iam_role" "eventbridge_lambda_role" {
  name = "${var.project_name}_eventbridge_lambda_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement: [
      {
        Effect    = "Allow",
        Principal = { Service = "events.amazonaws.com" },
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "eventbridge_lambda_policy" {
  name = "${var.project_name}_eventbridge_lambda_policy"
  role = aws_iam_role.eventbridge_lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement: [
      {
        Effect: "Allow",
        Action: [
          "lambda:InvokeFunction",
          "sagemaker:CreateEndpoint",
          "sagemaker:DescribeModel",
          "sagemaker:DescribeEndpoint",
          "sagemaker:UpdateEndpoint"
        ],
        Resource: "*"
      }
    ]
  })
}

resource "aws_iam_role" "lambda_exec_role" {
  name = "${var.project_name}_lambda_exec_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement: [
      {
        Action    = "sts:AssumeRole",
        Effect    = "Allow",
        Principal = { Service = "lambda.amazonaws.com" }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name   = "${var.project_name}_lambda_policy"
  role   = aws_iam_role.lambda_exec_role.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement: [
      {
        Effect: "Allow",
        Action: [
          "sagemaker:*",
          "s3:*",
          "logs:*",
          "lambda:InvokeFunction",
          "iam:PassRole",
          "events:PutEvents"
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

# Lambda Functions
resource "aws_lambda_function" "model_deployment_lambda" {
  function_name = "${var.project_name}_ModelDeploymentLambda"
  handler       = "lambda_function.lambda_handler"
  role          = aws_iam_role.lambda_exec_role.arn
  runtime       = "python3.8"
  s3_bucket     = "mysagemakerprojects"  
  s3_key        = "deployment-lambda.zip"
  environment {
    variables = {
      MODEL_GROUP_ARN           = "arn:aws:sagemaker:us-east-1:390403890405:model-package-group/PipelineModelPackageGroup"
      SAGEMAKER_EXECUTION_ROLE_ARN = "arn:aws:iam::390403890405:role/sagemaker-user-example"
    }
  }
}

resource "aws_lambda_function" "github_trigger_lambda" {
  function_name = "${var.project_name}_GitHubTriggerLambda"
  handler       = "lambda_function.lambda_handler"
  role          = aws_iam_role.lambda_exec_role.arn
  runtime       = "python3.8"
  s3_bucket     = "mysagemakerprojects"
  s3_key        = "github-trigger-lambda.zip"
  environment {
    variables = {
      GITHUB_REPO_OWNER = "isakovanilu"
      GITHUB_REPO_NAME  = "sagemaker_cancer_prediction"
      GITHUB_WORKFLOW   = "sagemaker_pipeline.yml"
    }
  }
}

# SageMaker Model Package Group (Model Registry)
resource "aws_sagemaker_model_package_group" "model_package_group" {
  model_package_group_name        = "PipelineModelPackageGroup"
  model_package_group_description = "Group for all versions of my machine learning model"
}

# EventBridge Rule and Target for Model Approval Trigger
resource "aws_cloudwatch_event_rule" "model_approval_rule" {
  name        = "${var.project_name}_ModelApprovalRule"
  description = "Trigger Lambda on SageMaker Model Package approval"
  event_pattern = jsonencode({
    "source": ["aws.sagemaker"],
    "detail-type": ["SageMaker Model Package State Change"],
    "detail": {
      "ModelPackageGroupName": [aws_sagemaker_model_package_group.model_package_group.model_package_group_name],
      "CurrentStatus": ["Approved"]
    }
  })
}

resource "aws_cloudwatch_event_target" "deployment_lambda_target" {
  rule      = aws_cloudwatch_event_rule.model_approval_rule.name
  target_id = "TriggerModelDeploymentLambda"
  arn       = aws_lambda_function.model_deployment_lambda.arn
}

resource "aws_lambda_permission" "allow_eventbridge_to_invoke_deployment_lambda" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.model_deployment_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.model_approval_rule.arn
}

# Output GitHub Actions URL
output "github_actions_url" {
  value       = "https://github.com/isakovanilu/sagemaker_cancer_prediction/actions"
  description = "GitHub Actions workflow URL to trigger the pipeline."
}
