import mediapackage_channel
import mediapackage_live_endpoint
import medialive_input
import medialive_channel
import mediatailor_configuration
import resource_tools
import datetime
import json
import sys


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
        #https://stackoverflow.com/questions/22296496/add-element-to-a-json-in-python
        event["ResourceProperties"]["PackagerPrimaryChannelUrl"] = "%s" % mp_channel["Data"][0]["Url"]
        event["ResourceProperties"]["PackagerPrimaryChannelUsername"] = "%s" % mp_channel["Data"][0]["Username"]
        event["ResourceProperties"]["PackagerPrimaryChannelPassword"] = "%s" % mp_channel["Data"][0]["Password"]
        event["ResourceProperties"]["PackagerSecondaryChannelUrl"] = "%s" % mp_channel["Data"][1]["Url"]
        event["ResourceProperties"]["PackagerSecondaryChannelUsername"] = "%s" % mp_channel["Data"][1]["Username"]
        event["ResourceProperties"]["PackagerSecondaryChannelPassword"] = "%s" % mp_channel["Data"][1]["Password"]
        event["ResourceProperties"]["ChannelId"] = "%s" % mp_channel["ResourceId"]
    if event['Debug'] == "ON":
        print("-----> Media Package Channel: {}\n".format(mp_channel))
        print("Event + Packager Info: {}\n".format(event))
        print("######################################################")


    mp_endpoint = mediapackage_live_endpoint.event_handler(event, context)
    if mp_endpoint["Status"] == "SUCCESS":
        event["ResourceProperties"]["MediaPackageOriginURL"] = "%s" % mp_endpoint["Data"]['OriginEndpointUrl']
        event["ResourceProperties"]["VideoContentSourceUrl"] = "%s" % mp_endpoint["Data"]["OriginEndpointUrl"].replace("index.m3u8", '')
    if event['Debug'] == "ON":
        print("-----> Media Endpoint: {}\n".format(mp_endpoint))
        print("Event + Media Package Origin Endpoint: {}\n".format(event))
        print("######################################################")


    ml_input = medialive_input.event_handler(event, context)
    if ml_input["Status"] == "SUCCESS":
        #https://stackoverflow.com/questions/22296496/add-element-to-a-json-in-python
        event["ResourceProperties"]["MediaLiveInputId"] = "%s" % ml_input["Data"]["Input"]["Id"]
    if event['Debug'] == "ON":
        print("-----> MediaLive Input: {}\n".format(ml_input))
        print("Event + Media Live Input Id: {}\n".format(event))
        print("######################################################")


    passwords = resource_tools.ssm_a_password(event, mp_channel)
    if passwords['Status'] == 'SUCCESS':
        ## Use %s instead of {} when working with Json
        event["ResourceProperties"]["PackagerPrimaryChannelPassword"] = '/medialive/%s-%s-0' % (event['ResourceProperties']['StackName'], event["LogicalResourceId"])
        event["ResourceProperties"]["PackagerSecondaryChannelPassword"] = '/medialive/%s-%s-1' % (event['ResourceProperties']['StackName'], event["LogicalResourceId"])
    if event['Debug'] == "ON":
        print("-----> Passwords Result: {}\n".format(passwords))
        print("Event + Password Params: {}\n".format(event))
        print("######################################################")


    ml_channel = medialive_channel.event_handler(event, context)
    if ml_channel['Status'] == 'SUCCESS':
        event["ResourceProperties"]["MediaLiveChannelId"] = "%s" % ml_channel["ResourceId"]
    if event['Debug'] == "ON":
        print("-----> MediaLive Result: {}\n".format(ml_channel))
        print("Event + MediaLive Channel: {}\n".format(event))
        print("######################################################")


    mt_config = mediatailor_configuration.event_handler(event, context)
    if mt_config['Status'] == 'SUCCESS':
        event["ResourceProperties"]["MediaTailorHlsUrl"] = "%s" % mt_config["Data"]["HlsConfiguration"]["ManifestEndpointPrefix"]

    debug("-----> MediaTailor Configuration: {}\n".format(mt_config))
    debug("Event {}\n".format(event))

    return event

def debug(message):
    if event['Debug'] == "ON":
        print(message)
        print("######################################################")



def out_to_file(event, context):
    current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = '%s-%s.json' % (event["ResourceProperties"]["StackName"], current_time)
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

    if event['Debug'] == "ON":
        print(event)
        print("######################################################")
    context = 0

    if ((event['RequestType'] == 'Create') and (resource_tools.does_exist(event, context) == False)):
        create = event_create(event, context)
        out_to_file(create, context)
        print("done")

    if event['RequestType'] == 'Delete':
        event_delete(event, context)

