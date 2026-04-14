import json
import os

import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")

SUMMARY_TABLE = os.environ["SUMMARY_TABLE"]
EVENTS_TABLE = os.environ["EVENTS_TABLE"]


def lambda_handler(event, context):
    params = event.get("queryStringParameters") or {}
    driver_id = params.get("driver_id")

    if driver_id:
        return get_driver(driver_id)
    return get_all_drivers()


def get_driver(driver_id):
    summary_table = dynamodb.Table(SUMMARY_TABLE)
    result = summary_table.get_item(Key={"driver_id": driver_id})
    item = result.get("Item")

    if not item:
        return {"statusCode": 404, "body": json.dumps({"error": f"driver {driver_id} not found"})}

    events_table = dynamodb.Table(EVENTS_TABLE)
    events = events_table.query(
        KeyConditionExpression=Key("driver_id").eq(driver_id),
        ScanIndexForward=False,
        Limit=20,
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "driver_id":    item["driver_id"],
            "score":        int(item["score"]),
            "last_updated": item["last_updated"],
            "recent_events": [
                {
                    "signal_type":  e["signal_type"],
                    "severity":     e["severity"],
                    "contribution": int(e["contribution"]),
                    "timestamp":    e["event_timestamp"],
                }
                for e in events["Items"]
            ],
        }),
    }


def get_all_drivers():
    summary_table = dynamodb.Table(SUMMARY_TABLE)
    result = summary_table.scan()
    drivers = sorted(result["Items"], key=lambda x: int(x["score"]), reverse=True)

    return {
        "statusCode": 200,
        "body": json.dumps([
            {
                "driver_id":    d["driver_id"],
                "score":        int(d["score"]),
                "last_updated": d["last_updated"],
            }
            for d in drivers
        ]),
    }
