import json
import os
import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")

ACTIONS_TABLE = os.environ["ACTIONS_TABLE"]
PLAYBOOK_TABLE = os.environ["PLAYBOOK_TABLE"]
SUMMARY_TABLE = os.environ["SUMMARY_TABLE"]

DEFAULT_PLAYBOOK = [
    {"signal_key": "customer_complaint#high",    "recommended_action": "1:1 conversation with driver within 24 hours"},
    {"signal_key": "customer_complaint#medium",  "recommended_action": "Address at next weekly check-in"},
    {"signal_key": "customer_complaint#low",     "recommended_action": "Monitor — flag if pattern continues"},
    {"signal_key": "on_road_observation#high",   "recommended_action": "Review incident details + schedule coaching"},
    {"signal_key": "on_road_observation#medium", "recommended_action": "Discuss at next check-in"},
    {"signal_key": "on_road_observation#low",    "recommended_action": "Log for awareness — no action required"},
    {"signal_key": "hard_braking#high",          "recommended_action": "Review dashcam footage + schedule defensive driving"},
    {"signal_key": "hard_braking#medium",        "recommended_action": "Monitor — no action unless pattern in 7 days"},
    {"signal_key": "hard_braking#low",           "recommended_action": "No action"},
]


def _format_playbook(items):
    result = []
    for item in items:
        signal_type, severity = item["signal_key"].split("#", 1)
        result.append({
            "signal_type": signal_type,
            "severity": severity,
            "recommended_action": item["recommended_action"],
        })
    return result


def get_dsp_id(event):
    try:
        return event["requestContext"]["authorizer"]["jwt"]["claims"]["custom:dsp_id"]
    except KeyError:
        return None


def lambda_handler(event, context):
    dsp_id = get_dsp_id(event)
    if not dsp_id:
        return {"statusCode": 401, "body": json.dumps({"error": "unauthorized"})}

    route = event.get("routeKey", "")

    if route == "POST /actions":
        return post_action(event, dsp_id)
    if route == "GET /playbook":
        return get_playbook(dsp_id)
    if route == "PUT /playbook":
        return put_playbook(event, dsp_id)

    return {"statusCode": 404, "body": json.dumps({"error": "not found"})}


def post_action(event, dsp_id):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return {"statusCode": 400, "body": json.dumps({"error": "invalid JSON"})}

    missing = {"driver_id", "action"} - body.keys()
    if missing:
        return {"statusCode": 400, "body": json.dumps({"error": f"missing fields: {sorted(missing)}"})}

    valid_actions = {"in_progress", "resolved", "snoozed"}
    if body["action"] not in valid_actions:
        return {"statusCode": 400, "body": json.dumps({"error": f"action must be one of {sorted(valid_actions)}"})}

    if body["action"] == "snoozed" and not body.get("snooze_until"):
        return {"statusCode": 400, "body": json.dumps({"error": "snooze_until required when action is snoozed"})}

    action_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    item = {
        "action_id":  action_id,
        "driver_id":  body["driver_id"],
        "dsp_id":     dsp_id,
        "status":     body["action"],
        "logged_by":  dsp_id,
        "logged_at":  now,
        "created_at": now,
    }
    if body.get("note"):
        item["action_note"] = body["note"]
    if body.get("snooze_until"):
        item["snoozed_until"] = body["snooze_until"]

    dynamodb.Table(ACTIONS_TABLE).put_item(Item=item)

    # Denormalize latest action_status onto driver summary for fast queue rendering
    dynamodb.Table(SUMMARY_TABLE).update_item(
        Key={"driver_id": body["driver_id"]},
        UpdateExpression="SET action_status = :s",
        ExpressionAttributeValues={":s": body["action"]},
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "action_id":  action_id,
            "driver_id":  body["driver_id"],
            "status":     body["action"],
            "logged_at":  now,
        }),
    }


def get_playbook(dsp_id):
    result = dynamodb.Table(PLAYBOOK_TABLE).query(
        KeyConditionExpression=Key("dsp_id").eq(dsp_id)
    )
    # Merge stored entries over defaults so all 9 signal/severity combos are always present
    merged = {e["signal_key"]: e["recommended_action"] for e in DEFAULT_PLAYBOOK}
    has_custom = bool(result["Items"])
    for item in result["Items"]:
        merged[item["signal_key"]] = item["recommended_action"]

    playbook = []
    for entry in DEFAULT_PLAYBOOK:  # preserve canonical ordering
        signal_type, severity = entry["signal_key"].split("#", 1)
        playbook.append({
            "signal_type": signal_type,
            "severity": severity,
            "recommended_action": merged[entry["signal_key"]],
        })

    return {
        "statusCode": 200,
        "body": json.dumps({
            "dsp_id":     dsp_id,
            "playbook":   playbook,
            "is_default": not has_custom,
        }),
    }


def put_playbook(event, dsp_id):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return {"statusCode": 400, "body": json.dumps({"error": "invalid JSON"})}

    updates = body.get("updates", [])
    if not updates:
        return {"statusCode": 400, "body": json.dumps({"error": "updates list required"})}

    valid_signal_types = {"hard_braking", "customer_complaint", "on_road_observation"}
    valid_severities = {"low", "medium", "high"}
    now = datetime.now(timezone.utc).isoformat()
    table = dynamodb.Table(PLAYBOOK_TABLE)

    for u in updates:
        if u.get("signal_type") not in valid_signal_types:
            return {"statusCode": 400, "body": json.dumps({"error": f"invalid signal_type: {u.get('signal_type')}"})}
        if u.get("severity") not in valid_severities:
            return {"statusCode": 400, "body": json.dumps({"error": f"invalid severity: {u.get('severity')}"})}
        if not u.get("recommended_action"):
            return {"statusCode": 400, "body": json.dumps({"error": "recommended_action required"})}
        if len(u["recommended_action"]) > 120:
            return {"statusCode": 400, "body": json.dumps({"error": "recommended_action max 120 characters"})}

        table.put_item(Item={
            "dsp_id":               dsp_id,
            "signal_key":           f"{u['signal_type']}#{u['severity']}",
            "recommended_action":   u["recommended_action"],
            "updated_at":           now,
        })

    return {"statusCode": 200, "body": json.dumps({"updated": len(updates)})}
