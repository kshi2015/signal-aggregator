import json
import os
import uuid
from datetime import datetime, timezone

import boto3

s3 = boto3.client("s3")
BUCKET = os.environ["RAW_EVENTS_BUCKET"]


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return {"statusCode": 400, "body": json.dumps({"error": "invalid JSON"})}

    required = {"driver_id", "signal_type", "severity", "timestamp", "source"}
    missing = required - body.keys()
    if missing:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"missing fields: {sorted(missing)}"}),
        }

    valid_signal_types = {"hard_braking", "customer_complaint", "on_road_observation"}
    if body["signal_type"] not in valid_signal_types:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"signal_type must be one of {sorted(valid_signal_types)}"}),
        }

    valid_severities = {"low", "medium", "high"}
    if body["severity"] not in valid_severities:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"severity must be one of {sorted(valid_severities)}"}),
        }

    event_id = body.get("event_id") or str(uuid.uuid4())
    body["event_id"] = event_id

    now = datetime.now(timezone.utc)
    key = f"events/{now.year}/{now.month:02d}/{now.day:02d}/{now.hour:02d}/{event_id}.json"

    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=json.dumps(body),
        ContentType="application/json",
    )

    return {
        "statusCode": 200,
        "body": json.dumps({"event_id": event_id, "s3_key": key}),
    }
