import mediapackage_channel
import mediapackage_live_endpoint
import medialive_input
import medialive_channel
import mediatailor_configuration
import resource_tools
import datetime
import json
import sys
import logging

##NOTES:
#### Use %s instead of {} when working with Json
#### https://stackoverflow.com/questions/22296496/add-element-to-a-json-in-python

log_level = "warning"
log_level = log_level.upper()  ## set log level to upper case

##works with AWS Logger: https://stackoverflow.com/questions/10332748/python-logging-setlevel
logger = logging.getLogger()
level = logging.getLevelName(log_level)
logger.setLevel(level)




def event_delete(event, context):
    mp_channel = 0

    if ('medialive' in event['pipeline']):
        medialive_channel.event_handler(event, context)
        medialive_input.event_handler(event, context)

    if ('mediapackage' in event['pipeline']):
        mediapackage_live_endpoint.event_handler(event, context)
        mediapackage_channel.event_handler(event, context)
        resource_tools.ssm_a_password(event, mp_channel)

    if ('mediatailor' in event['pipeline']):
        mediatailor_configuration.event_handler(event, context)
    print("Delete Complete")

def event_create(event, context):

    if ('mediapackage'in event['pipeline']):
        mp_channel = mediapackage_channel.event_handler(event, context)
        if mp_channel["Status"] == "SUCCESS":
            event["ResourceProperties"]["MP_Endpoints"] = mp_channel["Attributes"]
            event["ResourceProperties"]["ChannelId"] = "%s-%s" % (
                event['ResourceProperties']['StackName'], event["LogicalResourceId"]
            )
            event["ResourceProperties"]["MP_ARN"] = "%s" % mp_channel["Response"]["Arn"]
            logger.warning("Successfully Created MediaPackage Channel")
            logger.error("MediaPackage Channel: {}".format(mp_channel))
            logger.debug("Event + MediaPackage: {}".format(event))

        passwords = resource_tools.ssm_a_password(event, context)
        if passwords['Status'] == 'SUCCESS':
            event["ResourceProperties"]["MP_Endpoints"][0]["Password"] = '/medialive/%s-%s-0' % (
                event['ResourceProperties']['StackName'], event["LogicalResourceId"]
            )
            event["ResourceProperties"]["MP_Endpoints"][1]["Password"] = '/medialive/%s-%s-1' % (
                event['ResourceProperties']['StackName'], event["LogicalResourceId"]
            )
            logger.warning("Successfully Keystored Passwords")
            logger.error("Passwords Result: {}".format(passwords))
            logger.debug("Event + Password Params: {}".format(event))

        mp_endpoint = mediapackage_live_endpoint.event_handler(event, context)
        if mp_endpoint["Status"] == "SUCCESS":
            event["ResourceProperties"]["MediaPackageOriginURL"] = "%s" % (
                mp_endpoint["Attributes"]['OriginEndpointUrl']
            )
            event["ResourceProperties"]["VideoContentSourceUrl"] = "%s" % (
                mp_endpoint["Attributes"]["OriginEndpointUrl"].replace("index.m3u8", '')
            )
            logger.warning("Successfully Created MediaPackage Endpoint")
            logger.error("Media Endpoint: {}".format(mp_endpoint))
            logger.debug("Event + MediaPackage Endpoint: {}".format(event))


    if ('medialive'in event['pipeline']):
        ml_input = medialive_input.event_handler(event, context)
        if ml_input["Status"] == "SUCCESS":
            event["ResourceProperties"]["MediaLiveInputId"] = "%s" % ml_input['Attributes']['Id']
            event["pipeline"]['medialive']["ML_InputARN"] = "%s" % ml_input['Response']['Input']['Arn']
            logger.warning("Successfully Created ML Input")
            logger.error("MediaLive Input: {}".format(ml_input))
            logger.debug("Event + MediaLive Input: {}".format(event))

        ml_channel = medialive_channel.event_handler(event, context)
        if ml_channel['Status'] == 'SUCCESS':
            event["ResourceProperties"]["MediaLiveChannelId"] = "%s" % ml_channel['Attributes']
            event["pipeline"]['medialive']['ML_ARN'] = ml_channel['Response']['Channel']['Arn']
            logger.warning("Successfully Created MediaLive Channel")
            logger.error("MediaLive Result: {}".format(ml_channel))
            logger.debug("Event + MediaLive: {}".format(event))

    if ('mediatailor'in event['pipeline']):
        mt_config = mediatailor_configuration.event_handler(event, context)
        if mt_config['Status'] == 'SUCCESS':
            event["ResourceProperties"]["MediaTailorHlsUrl"] = "%s" % mt_config['Attributes']
            event['pipeline']['mediatailor'] = mt_config['Response']['PlaybackConfigurationArn']
            logger.warning("Successfully Created MediaTailor Configuration")
            logger.error("MediaTailor Configuration: {}".format(mt_config))
            logger.debug("Event + MediaTailor {}".format(event))

    return event

# def debug(message):
#     if event['Debug'] == "ON":
#         print(('----->  %s') % str(message))
#         print('######################################################\n')
#


def out_to_file(event, context):
    current_time = datetime.datetime.now().strftime("%H-%M")
    filename = '%s_%s.json' % (
        event["Name"], current_time
    )
    logger.debug('Json Output Filename: %s' % filename)

    with open(filename, 'w') as outfile:
        #https://stackoverflow.com/questions/12309269/how-do-i-write-json-data-to-a-file
        json.dump(event, outfile, sort_keys=True, indent=4, ensure_ascii=False)



if __name__ == "__main__":

    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = input("Please provide an input file: ")

    with open(filename) as json_file:
        event = json.load(json_file)
        logger.warning('Initial Event: %s' % event)

    context = 0

    if ((event['RequestType'] == 'Create') and (resource_tools.does_exist(event, context) == False)):
        create = event_create(event, context)
        out_to_file(create, context)
        print("Create Done")

    if event['RequestType'] == 'Delete':
        event_delete(event, context)