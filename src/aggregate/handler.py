import json
import os
from datetime import datetime, timezone, timedelta

import boto3
from boto3.dynamodb.conditions import Key

s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
sns_client = boto3.client("sns")

EVENTS_TABLE = os.environ["EVENTS_TABLE"]
SUMMARY_TABLE = os.environ["SUMMARY_TABLE"]
CONFIG_TABLE = os.environ["CONFIG_TABLE"]
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]

# Module-level cache — survives across warm invocations
_config_cache = None


def get_config():
    global _config_cache
    if _config_cache is None:
        table = dynamodb.Table(CONFIG_TABLE)
        response = table.get_item(Key={"config_key": "global"})
        _config_cache = response["Item"]
    return _config_cache


def lambda_handler(event, context):
    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]

        obj = s3_client.get_object(Bucket=bucket, Key=key)
        payload = json.loads(obj["Body"].read())

        score = process_event(payload)
        print(f"driver={payload['driver_id']} score={score} event={payload['event_id']}")


def process_event(payload):
    config = get_config()

    driver_id = payload["driver_id"]
    signal_type = payload["signal_type"]
    severity = payload["severity"]
    event_id = payload["event_id"]
    timestamp = payload["timestamp"]

    weight = int(config["weights"][signal_type])
    multiplier = int(config["severity_multipliers"][severity])
    contribution = weight * multiplier

    now = datetime.now(timezone.utc)
    ttl = int((now + timedelta(days=7)).timestamp())
    # SK format: ISO timestamp + event_id ensures uniqueness and enables range queries
    event_sk = f"{timestamp}#{event_id}"

    # Write this event's contribution
    events_table = dynamodb.Table(EVENTS_TABLE)
    events_table.put_item(Item={
        "driver_id":        driver_id,
        "event_sk":         event_sk,
        "signal_type":      signal_type,
        "severity":         severity,
        "contribution":     contribution,
        "event_timestamp":  timestamp,
        "ttl":              ttl,
    })

    # Recompute rolling score over the last 7 days
    window_days = int(config["window_days"])
    window_start = (now - timedelta(days=window_days)).isoformat()

    response = events_table.query(
        KeyConditionExpression=Key("driver_id").eq(driver_id) & Key("event_sk").gte(window_start)
    )
    score = sum(int(item["contribution"]) for item in response["Items"])

    # Update driver summary
    summary_table = dynamodb.Table(SUMMARY_TABLE)
    item = {
        "driver_id":    driver_id,
        "score":        score,
        "last_updated": now.isoformat(),
    }
    if "dsp_id" in payload:
        item["dsp_id"] = payload["dsp_id"]
    summary_table.put_item(Item=item)

    threshold = int(config["notification_threshold"])
    if score >= threshold:
        print(f"THRESHOLD CROSSED: driver={driver_id} score={score} threshold={threshold}")
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"Safety threshold crossed: {driver_id}",
            Message=json.dumps({
                "driver_id":  driver_id,
                "score":      score,
                "threshold":  threshold,
                "last_event": {"signal_type": signal_type, "severity": severity},
                "timestamp":  now.isoformat(),
            }),
        )

    return score
