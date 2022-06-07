import os
import site
import importlib
from setuptools.command import easy_install
install_path = os.environ['GLUE_INSTALLATION']

libraries = ["scikit-learn==0.22.0", "cloudpickle"]
for lib in libraries:
    easy_install.main( ["--install-dir", install_path, lib] )

importlib.reload(site)

import pandas as pd
import boto3
from sklearn.ensemble import RandomForestRegressor
from awsglue.utils import getResolvedOptions
import sys

args = getResolvedOptions(sys.argv,
                          ['bucket',
                           'prefix'])

data = pd.read_csv('http://data.insideairbnb.com/united-states/ny/new-york-city/2022-03-05/data/listings.csv.gz')

data['price'] = data['price'].str.replace('$','')
data['price'] = data['price'].str.replace(',','')
data['price'] = data['price'].astype(float)

x_cols = ['latitude','longitude','beds']
y_col = 'price'

data = data[x_cols + [y_col]].dropna().astype(float)
X, Y = data[x_cols], data[y_col]

model = RandomForestRegressor(max_depth=10)
model.fit(X, Y)

def write_cloudpickle(obj, bucket, key):
    import boto3
    import cloudpickle
    from io import BytesIO

    with BytesIO() as f:
        cloudpickle.dump(obj, f)
        f.seek(0)
        boto3.client('s3').upload_fileobj(Bucket=bucket, Key=key, Fileobj=f)

write_cloudpickle(
    model,
    bucket=args['bucket'],
    key=args['prefix'] + 'airbnb.pkl'
)