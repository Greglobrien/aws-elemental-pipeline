import mediapackage_channel
import mediapackage_live_endpoint
import medialive_input
import medialive_channel
import mediatailor_configuration
import resource_tools
import datetime
import json
import sys

##NOTES:
#### Use %s instead of {} when working with Json
#### https://stackoverflow.com/questions/22296496/add-element-to-a-json-in-python


def event_delete(event, context):
    mp_channel = 0
    medialive_channel.event_handler(event, context)
    mediapackage_live_endpoint.event_handler(event, context)
    mediapackage_channel.event_handler(event, context)
    medialive_input.event_handler(event, context)
    resource_tools.ssm_a_password(event, mp_channel)
    mediatailor_configuration.event_handler(event, context)


def event_create(event, context):

    mp_channel = mediapackage_channel.event_handler(event, context)
    if mp_channel["Status"] == "SUCCESS":
        event["ResourceProperties"]["PackagerPrimaryChannelUrl"] = "%s" % mp_channel["ResourceId"][0]["Url"]
        event["ResourceProperties"]["PackagerPrimaryChannelUsername"] = "%s" % mp_channel["ResourceId"][0]["Username"]
        event["ResourceProperties"]["PackagerPrimaryChannelPassword"] = "%s" % mp_channel["ResourceId"][0]["Password"]
        event["ResourceProperties"]["PackagerSecondaryChannelUrl"] = "%s" % mp_channel["ResourceId"][1]["Url"]
        event["ResourceProperties"]["PackagerSecondaryChannelUsername"] = "%s" % mp_channel["ResourceId"][1]["Username"]
        event["ResourceProperties"]["PackagerSecondaryChannelPassword"] = "%s" % mp_channel["ResourceId"][1]["Password"]
        event["ResourceProperties"]["ChannelId"] = "%s-%s" % (event['ResourceProperties']['StackName'], event["LogicalResourceId"])
        event["ResourceProperties"]["MediaPackgeARN"] = "%s" % mp_channel["Data"]["Arn"]

        debug("Media Package Channel: {}".format(mp_channel))
        debug("Event + Packager Channel: {}".format(event))


    mp_endpoint = mediapackage_live_endpoint.event_handler(event, context)
    if mp_endpoint["Status"] == "SUCCESS":
        event["ResourceProperties"]["MediaPackageOriginURL"] = "%s" % mp_endpoint["Data"]['OriginEndpointUrl']
        event["ResourceProperties"]["VideoContentSourceUrl"] = "%s" % mp_endpoint["Data"]["OriginEndpointUrl"].replace("index.m3u8", '')

        debug("Media Endpoint: {}".format(mp_endpoint))
        debug("Event + Media Package Origin Endpoint: {}".format(event))


    ml_input = medialive_input.event_handler(event, context)
    if ml_input["Status"] == "SUCCESS":
        event["ResourceProperties"]["MediaLiveInputId"] = "%s" % ml_input["Attributes"]["Id"]
        event["ResourceProperties"]["MediaLiveInputARN"] = "%s" % ml_input["Attributes"]["Arn"]

        debug("MediaLive Input: {}".format(ml_input))
        debug("Event + Media Live Input Id: {}".format(event))


    passwords = resource_tools.ssm_a_password(event, mp_channel)
    if passwords['Status'] == 'SUCCESS':
        event["ResourceProperties"]["PackagerPrimaryChannelPassword"] = '/medialive/%s-%s-0' % (event['ResourceProperties']['StackName'], event["LogicalResourceId"])
        event["ResourceProperties"]["PackagerSecondaryChannelPassword"] = '/medialive/%s-%s-1' % (event['ResourceProperties']['StackName'], event["LogicalResourceId"])

        debug("Passwords Result: {}".format(passwords))
        debug("Event + Password Params: {}".format(event))


    ml_channel = medialive_channel.event_handler(event, context)
    if ml_channel['Status'] == 'SUCCESS':
        event["ResourceProperties"]["MediaLiveChannelId"] = "%s" % ml_channel['ResourceId']

        debug("MediaLive Result: {}".format(ml_channel))
        debug("Event + MediaLive Channel: {}".format(event))


    mt_config = mediatailor_configuration.event_handler(event, context)
    if mt_config['Status'] == 'SUCCESS':
        event["ResourceProperties"]["MediaTailorHlsUrl"] = "%s" % mt_config['Attributes']

        debug("MediaTailor Configuration: {}".format(mt_config))
        debug("Event {}".format(event))

    return event

def debug(message):
    if event['Debug'] == "ON":
        print(('----->  %s') % str(message))
        print('######################################################\n')



def out_to_file(event, context):
    current_time = datetime.datetime.now().strftime("%H-%M")
    filename = '%s-%s_%s.json' % (event["ResourceProperties"]["StackName"], event["LogicalResourceId"], current_time)
    debug('Json Output Filename: %s' % filename)

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
        debug('Initial Event: %s' % event)

    context = 0

    if ((event['RequestType'] == 'Create') and (resource_tools.does_exist(event, context) == False)):
        create = event_create(event, context)
        out_to_file(create, context)
        print("done")

    if event['RequestType'] == 'Delete':
        event_delete(event, context)

