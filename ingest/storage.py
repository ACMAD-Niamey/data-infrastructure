"""MinIO / S3 client helpers for ingest."""

from __future__ import annotations

import json
import logging
import os

import boto3
from botocore.client import Config

log = logging.getLogger(__name__)


def s3_client():
    endpoint = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
    if not endpoint.startswith(("http://", "https://")):
        endpoint = f"http://{endpoint}"
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.getenv("MINIO_ROOT_USER", ""),
        aws_secret_access_key=os.getenv("MINIO_ROOT_PASSWORD", ""),
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def set_bucket_public(client, bucket: str) -> None:
    """Set bucket policy to allow public read on objects."""
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{bucket}/*"],
            }
        ],
    }
    try:
        client.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))
    except Exception as exc:
        log.warning("Failed to set public policy on bucket %s: %s", bucket, exc)
