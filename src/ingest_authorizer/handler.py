import json
import os

import boto3

_secret = None


def _get_secret():
    global _secret
    if _secret is None:
        client = boto3.client("secretsmanager")
        response = client.get_secret_value(SecretId=os.environ["SECRET_ARN"])
        _secret = response["SecretString"]
    return _secret


def lambda_handler(event, context):
    provided = (event.get("headers") or {}).get("x-api-key", "")
    if provided and provided == _get_secret():
        return {"isAuthorized": True}
    return {"isAuthorized": False}
