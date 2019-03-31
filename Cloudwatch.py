from botocore.vendored import requests
import boto3
import json
import string
import random
import time
import resource_tools



def out_to_file(names):
    filename = '%s_Cloudwatch.json' % (
        event["Name"]
    )
    resource_tools.debug('Json Output Filename: %s' % filename)

    with open(filename, 'w') as outfile:
        #https://stackoverflow.com/questions/12309269/how-do-i-write-json-data-to-a-file
        json.dump(names, outfile, sort_keys=True, indent=4, ensure_ascii=False)


def validate_alert(cloudwatch, name):
    alarm_check = {
        "AlarmNames": [
            name
        ]
    }
    response = cloudwatch.describe_alarms(**alarm_check)
    #print("Validate %s " % response)
    return response

def call_cloudwatch(cloudwatch, request):

    #print("call_cloudwatch: %s" % request)

    try:
        cloudwatch.put_metric_alarm(**request)
        check = validate_alert(cloudwatch, request["AlarmName"])
        if (check['ResponseMetadata']['HTTPStatusCode'] == 200):
            result = {
                'Status': 'SUCCESS',
                'Response': check
            }


    except Exception as ex:
        print(ex)
        result = {
            'Status': 'FAILED',
            'Data': {"Exception": str(ex)}
        }
    return result

def alarm_type1(event, sns, index):
    metric_name = "AudioLevel"
    channel_name = event["Name"]
    alarm_name = ("%s_%s_%s" % (metric_name, channel_name, index))
    ChannelId = event['ResourceProperties']['MediaLiveChannelId']
    AlarmDescription = "%s-Pipe-%s" % (event['ResourceProperties']['ChannelId'], index)

    type1 = {
        "AlarmName": alarm_name,
        "AlarmDescription": AlarmDescription,
        "ActionsEnabled": False,
        "OKActions": [
            sns
        ],
        "AlarmActions": [
            sns
        ],
        "InsufficientDataActions": [],
        "MetricName": "AudioLevel",
        "Namespace": "MediaLive",
        "Statistic": "Average",
        "Dimensions": [
            {
                "Name": "AudioDescriptionName",
                "Value": "audio_1080p5000000"
            },
            {
                "Name": "ChannelId",
                "Value": ChannelId
            },
            {
                "Name": "Pipeline",
                "Value": index
            }
        ],
        "Period": 120,
        "EvaluationPeriods": 1,
        "Threshold": -58.0,
        "ComparisonOperator": "LessThanOrEqualToThreshold",
        "TreatMissingData": "missing"
    }

    return type1


def alarm_type2 (event, sns, index):
    metric_name = "NetworkIn"
    channel_name = event["Name"]
    alarm_name = ("%s_%s_%s" % (metric_name, channel_name, index))
    ChannelId = event['ResourceProperties']['MediaLiveChannelId']
    AlarmDescription = "%s-Pipe-%s" % (event['ResourceProperties']['ChannelId'], index)

    type2 = {
        "AlarmName": alarm_name,
        "AlarmDescription": AlarmDescription,
        "ActionsEnabled": False,
        "OKActions": [
            sns
        ],
        "AlarmActions": [
            sns
        ],
        "InsufficientDataActions": [],
        "MetricName": "NetworkIn",
        "Namespace": "MediaLive",
        "Statistic": "Sum",
        "Dimensions": [
            {
                "Name": "ChannelId",
                "Value": ChannelId
            },
            {
                "Name": "Pipeline",
                "Value": index
            }
        ],
        "Period": 120,
        "EvaluationPeriods": 1,
        "DatapointsToAlarm": 1,
        "Threshold": 20000000.0,
        "ComparisonOperator": "LessThanOrEqualToThreshold",
        "TreatMissingData": "missing"
    }
    return type2


def create_alerts(cloudwatch, event, context):
    sns = "***REMOVED***"
    alarm_list = []
    audio_0 = alarm_type1(event, sns, "0")
    audio_resp_0 = call_cloudwatch(cloudwatch, audio_0)
    print(audio_resp_0)
    alarm_list.append(audio_resp_0["Response"]["MetricAlarms"][0]["AlarmName"])

    audio_1 = alarm_type1(event, sns, "1")
    audio_resp_1 = call_cloudwatch(cloudwatch, audio_1)
    print(audio_resp_1)
    alarm_list.append(audio_resp_1["Response"]["MetricAlarms"][0]["AlarmName"])

    network_0 = alarm_type2(event, sns, "0")
    network_resp_0 = call_cloudwatch(cloudwatch, network_0)
    print(network_resp_0)
    alarm_list.append(network_resp_0["Response"]["MetricAlarms"][0]["AlarmName"])

    network_1 = alarm_type2(event, sns, "1")
    network_resp_1 = call_cloudwatch(cloudwatch, network_1)
    print(network_resp_1)
    alarm_list.append(network_resp_1["Response"]["MetricAlarms"][0]["AlarmName"])

    print(alarm_list)

    alarmNames = {
        "AlarmNames": alarm_list
    }

    out_to_file(alarmNames)


def delete_alerts(cloudwatch, event, context):
    channel_name = event["Name"]

    alarm_check = {
        "AlarmNames": [
            "AudioLevel_%s_0" % channel_name,
            "AudioLevel_%s_1" % channel_name,
            "NetworkIn_%s_0" % channel_name,
            "NetworkIn_%s_1" % channel_name
        ]
    }
    delete = cloudwatch.delete_alarms(**alarm_check)

    return delete


def event_handler(event, context):
    """
    Lambda entry point. Print the event first.
    """
    resource_tools.debug("CloudWatch Event Input: %s " % event)
    try:
        cloudwatch = boto3.client('cloudwatch')
        if event["RequestType"] == "Create":
            result = create_alerts(cloudwatch, event, context)
        elif event["RequestType"] == "Update":
            result = update_alerts(cloudwatch, event, context)
        elif event["RequestType"] == "Delete":
            result = delete_alerts(cloudwatch, event, context)

    except Exception as exp:
        print("Exception: %s" % exp)
        result = {
            'Status': 'FAILED',
            'Data': {"Exception": str(exp)},
            'ResourceId': None
        }

    return result


with open('Dev-2019-03-21_11-50.json') as json_file:
    event = json.load(json_file)
    print('Initial Event: %s' % event)

event_handler(event, 0)