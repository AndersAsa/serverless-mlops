import pickle
from io import BytesIO
import boto3
import os
import json

def read_pickle(bucket, key):
    with BytesIO() as f:
        boto3.client('s3').download_fileobj(Bucket=bucket, Key=key, Fileobj=f)
        f.seek(0)
        return pickle.load(f)
print((os.environ['bucket'], os.environ['artifact_prefix'] + 'airbnb.pkl'))
model = read_pickle(os.environ['bucket'], os.environ['artifact_prefix'] + 'airbnb.pkl')

def predict(event, context):
    try:
        if 'body' in event: event = json.loads(event['body'])
        required_fields = ['longitude', 'latitude', 'beds']
        for field in required_fields:
            assert field in event.keys() and type(event[field]) in [int, float], f'No valid field {field}'
        X = [[ event['longitude'], event['latitude'], event['beds'] ]]
        pred = float(model.predict(X)[0])
        return {
                'statusCode':200,
                'prediction':pred
            }
    except:
        return {
                'statusCode':400
            }