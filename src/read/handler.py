import json
import os

import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")

SUMMARY_TABLE = os.environ["SUMMARY_TABLE"]
EVENTS_TABLE = os.environ["EVENTS_TABLE"]


def lambda_handler(event, context):
    params = event.get("queryStringParameters") or {}

    # Extracted from the Cognito JWT by API Gateway's JWT Authorizer —
    # callers cannot forge this value; it is set at user-creation time.
    try:
        dsp_id = event["requestContext"]["authorizer"]["jwt"]["claims"]["custom:dsp_id"]
    except KeyError:
        return {"statusCode": 401, "body": json.dumps({"error": "unauthorized"})}
    if not dsp_id:
        return {"statusCode": 401, "body": json.dumps({"error": "unauthorized"})}

    driver_id = params.get("driver_id")
    if driver_id:
        return get_driver(driver_id, dsp_id)
    return get_drivers_for_dsp(dsp_id)


def get_driver(driver_id, dsp_id):
    summary_table = dynamodb.Table(SUMMARY_TABLE)
    result = summary_table.get_item(Key={"driver_id": driver_id})
    item = result.get("Item")

    if not item:
        return {"statusCode": 404, "body": json.dumps({"error": f"driver {driver_id} not found"})}

    if item.get("dsp_id") != dsp_id:
        return {"statusCode": 403, "body": json.dumps({"error": "driver does not belong to this DSP"})}

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


def get_drivers_for_dsp(dsp_id):
    summary_table = dynamodb.Table(SUMMARY_TABLE)
    # PoC: scan + filter. Production: replace with GSI query on dsp_id
    result = summary_table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr("dsp_id").eq(dsp_id)
    )
    drivers = sorted(result["Items"], key=lambda x: int(x["score"]), reverse=True)

    return {
        "statusCode": 200,
        "body": json.dumps([
            {
                "driver_id":     d["driver_id"],
                "score":         int(d["score"]),
                "last_updated":  d["last_updated"],
                "action_status": d.get("action_status"),
            }
            for d in drivers
        ]),
    }
