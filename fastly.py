import json
from urllib.parse import urlparse


def debug(message):
    if event['Debug'] == "ON":
        print("-----> {}".format(message))
        print("######################################################")



def fastly_vcl_dictionary(event, context):
    #https://docs.python.org/3.7/library/urllib.parse.html?highlight=urlparse
    mediatailor_parse = urlparse(event["ResourceProperties"]["MediaTailorHlsUrl"])
    mediatailor_path = mediatailor_parse.path
    mediatailor_fastly = mediatailor_path[:-1] # removes trailing slash only
    debug("MediaTailor Parse: {}".format(str(mediatailor_parse)))

    mediapackage_parse = urlparse(event["ResourceProperties"]["MediaPackageOriginURL"])
    mediapackage_path = mediapackage_parse.path
    mediapackage_fastly = mediapackage_path.replace("/index.m3u8", '')
    debug("MediaPackage Parse: {}".format(str(mediapackage_parse)))

    vcl_dictionary = {
        "items": [
            {
                "op": "update",
                "item_key": "1-1-aws-mediatailor-path",
                "item_value": "%s" % mediatailor_fastly,
            },
            {
                "op": "update",
                "item_key": "1-aws-mediatailor-url",
                "item_value": "%s" % mediatailor_parse.netloc
            },
            {
                "op": "update",
                "item_key": "2-1-aws-mediapackage-path",
                "item_value": "%s" % mediapackage_fastly,
            },
            {
                "op": "update",
                "item_key": "2-aws-mediapackage-url",
                "item_value": "%s" % mediapackage_parse.netloc,
            }
        ]
    }

    debug("VCL_Dictionary: {}".format(vcl_dictionary))

    filename = 'Fastly-Dictionary-%s-%s.json' % (event["ResourceProperties"]["StackName"], event["LogicalResourceId"])
    debug("Json Output Filename: {}".format(filename))
    with open(filename, 'w') as outfile:
        #https://stackoverflow.com/questions/12309269/how-do-i-write-json-data-to-a-file
        json.dump(vcl_dictionary, outfile, sort_keys=True, indent=4, ensure_ascii=False)





if __name__ == "__main__":

    with open('deploy-2019-01-18_15-07.json') as json_file:
        event = json.load(json_file)

    if event['Debug'] == "ON":
        print(event)
        print("######################################################")
    context = 0

    if event['RequestType'] == 'Create':
        create = fastly_vcl_dictionary(event, context)
