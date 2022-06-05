import datetime
import os
import boto3
import json
import time

def snapshot(bucket, prefix):
    assert 'latest' in prefix, f'Artifact path {prefix} does not contain "latest"'
    s3_client = boto3.client('s3')
    snapshot_folder = str(datetime.datetime.utcnow())

    files = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    file_keys = [f['Key'] for f in files['Contents']]

    for f in file_keys:
        new_key = f.replace('latest',snapshot_folder)
        s3_client.copy(
            Bucket=bucket,
            Key=new_key,
            CopySource={"Bucket":bucket, "Key":f}
        )
    return snapshot_folder

def test_app(event):
    lambda_client = boto3.client('lambda')


    response = lambda_client.invoke(
        FunctionName=f'{os.environ["inference"]}:latest',
        Payload=json.dumps(event).encode()
    )

    parsed = json.loads(response["Payload"].read())
    return True if parsed['statusCode'] == 200 else False



def deploy(event, context):
    '''
    Test the inference app lambda
    Create a snapshot of the model artifacts
    Publish a new lambda version pointing to the snapshot
    Change the challenger alias to point at the new version
    '''
    inference_lambda = os.environ['inference']
    bucket, prefix = os.environ['bucket'], os.environ['prefix']

    lambda_client = boto3.client('lambda')

    # Test the inference app lambda
    event = json.load(open('event.json'))
    assert test_app(event), 'Inference API does not return status 200'
    
    # Create a snapshot of the model artifacts
    snapshot_folder = snapshot(bucket, prefix)

    # Retrieve configuration of LATEST inference lambda
    inference_function = lambda_client.get_function_configuration(
        FunctionName=inference_lambda
    )["Environment"]

    # Change artifacts folder from latest to the new snapshot
    inference_function['Variables']['artifact_prefix'] = (
        inference_function['Variables']['artifact_prefix']
        .replace('latest',snapshot_folder)
    )

    # Update the LATEST lambda version
    lambda_client.update_function_configuration(
        FunctionName=inference_lambda,
        Environment=inference_function
    )
    time.sleep(5)
    
    # Publish a new lambda version pointing to the snapshot
    new_version = lambda_client.publish_version(
        FunctionName=inference_lambda
    )['Version']

    # Change LATEST lambda version's path back to the latest model artifacts
    inference_function['Variables']['artifact_prefix'] = (
        inference_function['Variables']['artifact_prefix']
        .replace(snapshot_folder, 'latest')
    )
    lambda_client.update_function_configuration(
        FunctionName=inference_lambda,
        Environment=inference_function
    )
    

    # Change the challenger alias to point at the new version
    lambda_client.update_alias(
        FunctionName=inference_lambda,
        Name='challenger',
        FunctionVersion=new_version
    )

    return {
        'statusCode':200,
        'Body':"Tests passed and model deployed"
    }