#!/usr/bin/env python
"""
One-time script to set existing MinIO buckets to public read access.
Run this to fix already-created buckets.
"""
import os
import json
import boto3
from botocore.client import Config

def s3_client():
    endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
    if not endpoint.startswith(("http://", "https://")):
        endpoint = f"http://{endpoint}"
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.getenv("MINIO_ROOT_USER", "minioadmin"),
        aws_secret_access_key=os.getenv("MINIO_ROOT_PASSWORD", "minioadmin"),
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )

def set_bucket_public(client, bucket: str):
    """Set bucket policy to allow public read access."""
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{bucket}/*"]
            }
        ]
    }
    
    try:
        client.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))
        return True
    except Exception as e:
        print(f"  Warning: {e}")
        return False

def main():
    print("Connecting to MinIO...")
    client = s3_client()
    
    # List all buckets
    response = client.list_buckets()
    buckets = [b['Name'] for b in response['Buckets']]
    
    print(f"\nFound {len(buckets)} bucket(s): {buckets}\n")
    
    # Set each to public
    for bucket in buckets:
        print(f"Setting '{bucket}' to public read-only...")
        if set_bucket_public(client, bucket):
            print(f"  '{bucket}' is now publicly readable\n")
        else:
            print(f"  Failed to set '{bucket}' public\n")
    
    print("=" * 60)
    print("Done. Test with:")
    print(f"   curl -I http://localhost:9000/{{bucket}}/{{key}}")
    print("=" * 60)

if __name__ == "__main__":
    main()
