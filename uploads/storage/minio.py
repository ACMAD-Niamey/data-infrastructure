import os
import boto3
from botocore.client import Config

def minio_client():
    endpoint = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
    # Ensure endpoint has protocol prefix
    if not endpoint.startswith(("http://", "https://")):
        endpoint = f"http://{endpoint}"
    
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ["MINIO_ROOT_USER"],
        aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"],
        region_name=os.getenv("MINIO_REGION", "us-east-1"),
        config=Config(signature_version="s3v4"),
    )
