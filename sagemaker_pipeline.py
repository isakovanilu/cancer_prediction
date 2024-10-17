import boto3
import sagemaker
from sagemaker import get_execution_role
from sagemaker.estimator import Estimator
from sagemaker.inputs import TrainingInput
from sagemaker.processing import ProcessingInput, ProcessingOutput
from sagemaker.sklearn.processing import SKLearnProcessor
from sagemaker.workflow.parameters import ParameterString
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.step_collections import RegisterModel
from sagemaker.workflow.steps import ProcessingStep, TrainingStep

# Set region explicitly
region = "us-east-1"  # Change to your desired AWS region
sess = boto3.Session(region_name=region)
sagemaker_session = sagemaker.Session(boto_session=sess)

# Define bucket, prefix, and role
bucket = "mysagemakerprojects"
prefix = "linear-learner-pipeline"
role = "arn:aws:iam::390403890405:role/sagemaker-user-example"
# Alternatively, use get_execution_role() if appropriate
# role = get_execution_role()

# Define model package group name
MODEL_PACKAGE_GROUP_NAME = "LinearLearnerModelPackageGroup"

# Define pipeline parameters
train_data_param = ParameterString(
    name="TrainData",
    default_value=f"s3://{bucket}/{prefix}/input/test-data.csv",
)
output_prefix_param = ParameterString(
    name="OutputPrefix",
    default_value=f"s3://{bucket}/{prefix}/processed/",
)
instance_type_param = ParameterString(
    name="InstanceType",
    default_value="ml.m5.xlarge",
)

# Define the Scikit-learn processor for data preprocessing
sklearn_processor = SKLearnProcessor(
    framework_version="1.0-1",  # Adjust based on your sklearn version
    role=role,
    instance_type=instance_type_param,
    instance_count=1,
    sagemaker_session=sagemaker_session,
)

# Define the ProcessingStep
processing_step = ProcessingStep(
    name="DataProcessingStep",
    processor=sklearn_processor,
    inputs=[
        ProcessingInput(
            source=train_data_param,
            destination="/opt/ml/processing/input",  # Container path
        )
    ],
    outputs=[
        ProcessingOutput(
            source="/opt/ml/processing/output/train/",  # Container path for train.csv
            destination=f"s3://{bucket}/{prefix}/processed/train/",
            output_name="train_data",
        ),
        ProcessingOutput(
            source="/opt/ml/processing/output/validation/",  # Container path for validation.csv
            destination=f"s3://{bucket}/{prefix}/processed/validation/",
            output_name="validation_data",
        ),
    ],
    code="preprocessing.py",  # Ensure this script is in your working directory
)

# Define the Linear Learner Estimator
linear_estimator = Estimator(
    image_uri=sagemaker.image_uris.retrieve("linear-learner", region),
    role=role,
    instance_count=1,
    instance_type="ml.m5.large",
    volume_size=30,  # in GB
    max_run=3600,  # in seconds
    output_path=f"s3://{bucket}/{prefix}/output/",
    sagemaker_session=sagemaker_session,
)

# Set hyperparameters for the Linear Learner
linear_estimator.set_hyperparameters(
    predictor_type="binary_classifier",
    mini_batch_size=10,
)

# Define the TrainingStep
training_step = TrainingStep(
    name="TrainLinearLearnerModel",
    estimator=linear_estimator,
    inputs={
        "train": TrainingInput(
            s3_data=processing_step.properties.ProcessingOutputConfig.Outputs[
                "train_data"
            ].S3Output.S3Uri,
            content_type="text/csv",
        ),
        "validation": TrainingInput(
            s3_data=processing_step.properties.ProcessingOutputConfig.Outputs[
                "validation_data"
            ].S3Output.S3Uri,
            content_type="text/csv",
        ),
    },
)

# Define the Model Registration Step
model_register_step = RegisterModel(
    name="RegisterLinearLearnerModel",
    estimator=linear_estimator,
    model_data=training_step.properties.ModelArtifacts.S3ModelArtifacts,
    content_types=["text/csv"],
    response_types=["text/csv"],
    inference_instances=["ml.m5.large"],
    transform_instances=["ml.m5.large"],
    model_package_group_name=MODEL_PACKAGE_GROUP_NAME,
)

# Define the Pipeline
pipeline = Pipeline(
    name="LinearLearnerPipeline",
    steps=[processing_step, training_step, model_register_step],
    parameters=[
        train_data_param,
        output_prefix_param,
        instance_type_param,
    ],
    sagemaker_session=sagemaker_session,
)

# Create or update the pipeline
pipeline.upsert(role_arn=role)

# Execute the pipeline
pipeline_execution = pipeline.start()

print(f"Pipeline execution started with execution ARN: {pipeline_execution.arn}")

# Wait for the pipeline execution to complete before deploying the endpoint
pipeline_execution.wait()
