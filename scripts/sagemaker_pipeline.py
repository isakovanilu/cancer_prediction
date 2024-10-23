import sagemaker
import boto3
from sagemaker import get_execution_role
from sagemaker.processing import ProcessingInput, ProcessingOutput, ScriptProcessor
from sagemaker.sklearn.processing import SKLearnProcessor
from sagemaker.workflow.steps import ProcessingStep, TrainingStep
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.pipeline_context import PipelineSession
from sagemaker.workflow.parameters import ParameterString
from sagemaker.inputs import TrainingInput
from sagemaker.estimator import Estimator
from sagemaker.workflow.step_collections import RegisterModel
from sagemaker.workflow.steps import CreateModelStep, TransformStep
from sagemaker.workflow.model_step import ModelStep
from sagemaker.workflow.pipeline import Pipeline
from sagemaker import Model
from sagemaker.inputs import CreateModelInput
from sagemaker import ModelPackage

from sagemaker.transformer import Transformer
from sagemaker.inputs import TransformInput


# Set region explicitly
region = "us-east-1"  # Change to your desired AWS region
sess = boto3.Session(region_name=region)

# Initialize SageMaker session and role
sagemaker_session = sagemaker.Session(boto_session=sess)


role="arn:aws:iam::390403890405:role/sagemaker-user-example"
# role = get_execution_role()
bucket = "mysagemakerprojects"
prefix = 'xgboost'
MODEL_PACKAGE_GROUP_NAME="PipelineModelPackageGroup"

# Define Pipeline Parameters (optional for flexibility)
train_data_param = ParameterString(
    name='TrainData',
    default_value=f's3://{bucket}/{prefix}/input/test-data.csv'
)
output_prefix_param = ParameterString(
    name='OutputPrefix',
    default_value=f's3://{bucket}/{prefix}/processed/'
)
instance_type_param = ParameterString(
    name='InstanceType',
    default_value='ml.m5.xlarge'
)

# Define the Scikit-learn processor for data preprocessing
sklearn_processor = SKLearnProcessor(
    framework_version='1.0-1',  # Adjust based on your sklearn version
    role=role,
    instance_type='ml.m5.xlarge',  # Using a fixed instance type
    instance_count=1,
    sagemaker_session=sagemaker_session
)

# Define the ProcessingStep
processing_step = ProcessingStep(
    name="DataProcessingStep",
    processor=sklearn_processor,
    inputs=[
        ProcessingInput(
            source=train_data_param,  # S3 path to test-data.csv
            destination='/opt/ml/processing/input'  # Container path
        )
    ],
    outputs=[
        ProcessingOutput(
            source='/opt/ml/processing/output/train/',  # Container path for train.csv
            destination=f's3://{bucket}/{prefix}/processed/train/',  # S3 path
            output_name='train_data'  # This is the name of the output
        ),
        ProcessingOutput(
            source='/opt/ml/processing/output/validation/',  # Container path for validation.csv
            destination=f's3://{bucket}/{prefix}/processed/validation/',  # S3 path
            output_name='validation_data'  # This is the name of the validation output
        )
    ],
    code="scripts/preprocessing.py"  # Ensure this script is in your working directory
)

# Define the XGBoost Estimator
xgboost_estimator = Estimator(
    image_uri=sagemaker.image_uris.retrieve("xgboost", region, version="1.3-1"),  # XGBoost version
    role=role,
    instance_count=1,
    instance_type='ml.m5.xlarge',
    volume_size=30,  # in GB
    max_run=3600,  # in seconds
    output_path=f's3://{bucket}/{prefix}/output/',
    sagemaker_session=sagemaker_session
)

# Set hyperparameters for XGBoost
xgboost_estimator.set_hyperparameters(
    objective='binary:logistic',  # Binary classification objective
    max_depth=5,
    eta=0.2,
    gamma=4,
    min_child_weight=6,
    subsample=0.8,
    verbosity=1,
    num_round=100
)


################
# Define TrainingStep using the correct outputs from ProcessingStep
training_step = TrainingStep(
    name="TrainXGBoostModel",
    estimator=xgboost_estimator,
    inputs={
        'train': TrainingInput(
            s3_data=processing_step.properties.ProcessingOutputConfig.Outputs["train_data"].S3Output.S3Uri,  # Correct reference to 'train_data'
            content_type='text/csv'
        ),
        'validation': TrainingInput(
            s3_data=processing_step.properties.ProcessingOutputConfig.Outputs["validation_data"].S3Output.S3Uri,  # Correct reference to 'validation_data'
            content_type='text/csv'
        )
    }
)


# Define the ProcessingStep for model evaluation
evaluation_processor = ScriptProcessor(
    image_uri=xgboost_estimator.training_image_uri(),  # Use the same image as training
    command=['python3'],
    instance_type='ml.m5.xlarge',
    instance_count=1,
    role=role,
    sagemaker_session=sagemaker_session
)

evaluation_step = ProcessingStep(
    name="ModelEvaluationStep",
    processor=evaluation_processor,
    inputs=[
        ProcessingInput(
            source=training_step.properties.ModelArtifacts.S3ModelArtifacts,  # Reference the trained model
            destination='/opt/ml/processing/model'  # Where the model will be stored in the container
        ),
        ProcessingInput(
            source=processing_step.properties.ProcessingOutputConfig.Outputs["validation_data"].S3Output.S3Uri,  # S3 path to the test data
            destination='/opt/ml/processing/output/validation/'  # Container path for the test data
        )
    ],
    outputs=[
        ProcessingOutput(
            source='/opt/ml/processing/output/evaluation/',  # Container path for evaluation results
            destination=f's3://{bucket}/{prefix}/evaluation/',  # S3 path to save evaluation results
            output_name='evaluation_report'
        )
    ],
    code="scripts/evaluation.py"  # The evaluation script
)

# Define Model Registration Step
model_register_step = RegisterModel(
    name="RegisterXGBoostModel",
    estimator=xgboost_estimator,
    model_data=training_step.properties.ModelArtifacts.S3ModelArtifacts,
    content_types=["text/csv"],
    response_types=["text/csv"],
    inference_instances=["ml.m5.large"],
    transform_instances=["ml.m5.large"],
    model_package_group_name=MODEL_PACKAGE_GROUP_NAME
)

# Add the evaluation step to the pipeline steps
pipeline = Pipeline(
    name="XGBoostPipeline",
    steps=[processing_step, training_step, evaluation_step, model_register_step],
    parameters=[
        train_data_param,
        output_prefix_param,
        instance_type_param
    ],
    sagemaker_session=sagemaker_session
)

# Create or update the pipeline
pipeline.upsert(role_arn=role)

# Execute the pipeline
pipeline_execution = pipeline.start()

print(f"Pipeline execution started with execution ARN: {pipeline_execution.arn}")
