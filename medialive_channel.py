"""
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""

from botocore.vendored import requests
import boto3
import json
import string
import random
import time
import resource_tools


def event_handler(event, context):
    """
    Lambda entry point. Print the event first.
    """
    resource_tools.debug("MediaLive Event Input: %s " % event)
    try:
        medialive = boto3.client('medialive')
        if event["RequestType"] == "Create":
            result = create_channel(medialive, event, context)
        elif event["RequestType"] == "Update":
            result = update_channel(medialive, event, context)
        elif event["RequestType"] == "Delete":
            result = delete_channel(medialive, event, context)

    except Exception as exp:
        print("Exception: %s" % exp)
        result = {
            'Status': 'FAILED',
            'Data': {"Exception": str(exp)},
            'ResourceId': None
        }

    return result


def create_channel(medialive, event, context, auto_id=True):
    """
    Create a MediaLive channel
    Return the channel URL, username and password generated by MediaLive
    """

    if auto_id:
        channel_id = "%s-%s" % (resource_tools.stack_name(event), event["LogicalResourceId"])
    else:
        channel_id = event["PhysicalResourceId"]

    try:

        destinations = event['ResourceProperties']['MP_Endpoints']
        resource_tools.debug("ML Destinations are: %s" % destinations)

        response = create_live_channel(
            event["ResourceProperties"]["MediaLiveInputId"], channel_id,
            event["ResourceProperties"]["Resolutions"],destinations,
            event["ResourceProperties"]["MediaLiveAccessRoleArn"], medialive
        )

        attributes = response['Channel']['Id']

        result = {
            'Status': 'SUCCESS',
            'Attributes': attributes,
            'Response': response
        }
        resource_tools.debug("ML Result %s" % result)
        # wait until the channel is idle, otherwise the lambda will time out

        resource_tools.wait_for_channel_states(medialive, attributes, ['IDLE'])

        if event['State'] == "ON":
            medialive.start_channel(ChannelId=attributes)

    except Exception as ex:
        print(ex)
        result = {
            'Status': 'FAILED',
            'Data': {"Exception": str(ex)},
            'ResourceId': attributes
        }

    return result


def update_channel(medialive, event, context):
    """
    Update a MediaLive channel
    Return the channel URL, username and password generated by MediaLive
    """

    if 'PhysicalResourceId' in event:
        channel_id = event["PhysicalResourceId"]
    else:
        channel_id = "%s-%s" % (resource_tools.stack_name(event), event["LogicalResourceId"])

    try:
        result = delete_channel(medialive, event, context)
        if result['Status'] == 'SUCCESS':
            result = create_channel(medialive, event, context, False)

    except Exception as ex:
        print(ex)
        result = {
            'Status': 'FAILED',
            'Data': {"Exception": str(ex)},
            'ResourceId': channel_id
        }

    return result


def delete_channel(medialive, event, context):
    """
    Delete a MediaLive channel
    Return success/failure
    """

    if 'PhysicalResourceId' in event:
        channel_id = event["PhysicalResourceId"]
    else:
        channel_id = event["ResourceProperties"]["MediaLiveChannelId"]

    try:
        # stop the channel
        medialive.stop_channel(ChannelId=channel_id)
        # wait untl the channel is idle, otherwise the lambda will time out
        resource_tools.wait_for_channel_states(medialive, channel_id, ['IDLE'])

    except Exception as ex:
        # report it and continue
        print(ex)

    try:
        response = medialive.delete_channel(ChannelId=channel_id)
        result = {
            'Status': 'SUCCESS',
            'Data': {},
            'ResourceId': channel_id
        }

    except Exception as ex:
        print(ex)
        result = {
            'Status': 'FAILED',
            'Data': {"Exception": str(ex)},
            'ResourceId': channel_id
        }

    return result


def get_video_description(w, h, b, n):
    video_description = {
        'Height': int(h),
        'Width': int(w),
        'CodecSettings': {
            'H264Settings': {
                'AdaptiveQuantization': 'HIGH',
                'AfdSignaling': 'NONE',
                'Bitrate': int(b),
                'BufSize': int(b * 2),
                'BufFillPct': 90,
                'ColorMetadata': 'INSERT',
                'EntropyEncoding': 'CABAC',
                'FlickerAq': 'ENABLED',
                'FramerateControl': 'SPECIFIED',
                'FramerateDenominator': 1,
                'FramerateNumerator': 30,
                'GopBReference': 'DISABLED',
                'GopClosedCadence': 1,
                'GopNumBFrames': 1,
                'GopSize': 2,
                'GopSizeUnits': 'SECONDS',
                'Level': 'H264_LEVEL_AUTO',
                'LookAheadRateControl': 'HIGH',
                'NumRefFrames': 3,
                'ParControl': 'INITIALIZE_FROM_SOURCE',
                'Profile': str(get_video_profile(h)),
                'RateControlMode': 'CBR',
                'ScanType': 'PROGRESSIVE',
                'SceneChangeDetect': 'ENABLED',
                'Slices': 1,
                'SpatialAq': 'ENABLED',
                'Syntax': 'DEFAULT',
                'TemporalAq': 'ENABLED',
                'TimecodeInsertion': 'DISABLED'
            }
        },
        'Name': str(n),
        'RespondToAfd': 'NONE',
        'Sharpness': 100,
        'ScalingBehavior': 'DEFAULT',
    }
    return video_description

def get_video_profile(h):
    profile = 'MAIN'
    if h > 719:
        profile = 'HIGH'
    return profile

def get_output(n):
    output = {
        'OutputSettings': {
            'HlsOutputSettings': {
                'NameModifier': '_' + str(n),
                'HlsSettings': {
                    'StandardHlsSettings': {
                        'AudioRenditionSets': 'PROGRAM_AUDIO',
                        'M3u8Settings': {
                            'AudioFramesPerPes': 4,
                            'AudioPids': '492-498',
                            'EcmPid': '8182',
                            'PcrControl': 'PCR_EVERY_PES_PACKET',
                            'PmtPid': '480',
                            'ProgramNum': 1,
                            'Scte35Behavior': 'PASSTHROUGH',
                            'Scte35Pid': '500',
                            'TimedMetadataBehavior': 'NO_PASSTHROUGH',
                            'TimedMetadataPid': '502',
                            'VideoPid': '481'
                        }
                    }
                }
            }
        },
        'OutputName': str(n),
        'VideoDescriptionName': str(n),
        'AudioDescriptionNames': ['audio_' + str(n)],
        'CaptionDescriptionNames': ['caption_' + str(n)]
    }
    print("This is the Name %s" % str(n))
    print("This is the OUTPUT for %s \n" % output)
    return output


def get_encoding_settings(layer, bitrateperc=1.0, framerate=1.0):
    # recommended bitrates for workshop samples
    c = {
        '1080': {'width': 1920, 'height': 1080, 'bitrate': 5000000},
        '720': {'width': 1280,  'height': 720,  'bitrate': 3500000},
        '540': {'width': 960,   'height': 540,  'bitrate': 2500000},
        '480': {'width': 852,   'height': 480,  'bitrate': 1800000},
        '360': {'width': 640,   'height': 360,  'bitrate': 1400000},
        '359': {'width': 640,   'height': 360,  'bitrate':  900000},
        '234': {'width': 416,   'height': 234,  'bitrate':  600000},
        '233': {'width': 416,   'height': 234,  'bitrate':  300000}
    }
    this_layer = c[layer]
    this_layer['bitrate'] = int(
        float(float(this_layer['bitrate']) * bitrateperc) * framerate)
    return this_layer


def get_caption_descriptions(specs):
    caption = {
        "CaptionSelectorName": "EmbeddedSelector",
        "DestinationSettings": {
            "EmbeddedDestinationSettings": {}
        },
        "LanguageCode": "",
        "LanguageDescription": "",
        "Name": str('caption_' + specs)
    }
    return caption


def get_audio_descriptions(specs):
    audio = {
                'AudioSelectorName': 'Default',
                'AudioTypeControl': 'FOLLOW_INPUT',
                'CodecSettings': {
                    'AacSettings': {
                        'Bitrate': 128000,
                        'CodingMode': 'CODING_MODE_2_0',
                        'InputType': 'NORMAL',
                        'Profile': 'LC',
                        'RateControlMode': 'CBR',
                        'RawFormat': 'NONE',
                        'SampleRate': 48000,
                        'Spec': 'MPEG4'
                    }
                },
                'LanguageCodeControl': 'FOLLOW_INPUT',
                'Name': str('audio_' + specs)
    }
    print("get_audio_Description: %s " % audio)
    return audio


def audio_only():
    audio_only = {
        'AudioDescriptionNames': [
            'audio_only'
        ],
        'CaptionDescriptionNames': [],
        'OutputName': 'w7a67',
        'OutputSettings': {
            'HlsOutputSettings': {
                'HlsSettings': {
                    'AudioOnlyHlsSettings': {
                        'AudioGroupId': 'PROGRAM_AUDIO',
                        'AudioTrackType': 'AUDIO_ONLY_VARIANT_STREAM'
                    }
                },
                'NameModifier': '_AudioOnly'
            }
        }
    }
    return audio_only

def create_live_channel(input_id, channel_name, layers, destinations, arn, medialive):
    video_descriptions = []
    outputs = []
    captions = []
    audio_descriptions = []
    # go through each layer
    for l in layers:
        if isinstance(l, int):
            c = get_encoding_settings(str(l))
        else:
            c = get_encoding_settings(str(l['height']), l['bitrateperc'])
        video_description = get_video_description(
            c['width'], c['height'], c['bitrate'], str(str(c['height']) + 'p' + str(c['bitrate'])))
        video_descriptions.append(video_description)

        output = get_output(str(str(c['height']) + 'p' + str(c['bitrate'])))
        outputs.append(output)

        caption = get_caption_descriptions(str(str(c['height']) + 'p' + str(c['bitrate'])))
        captions.append(caption)

        audio = get_audio_descriptions(str(str(c['height']) + 'p' + str(c['bitrate'])))
        audio_descriptions.append(audio)

    #audio_output = audio_only()
    #outputs.append(audio_output)

    #only = "only"
    #audio2 = get_audio_descriptions(only)
    #audio_descriptions.append(audio2)

    print(outputs)
    print("##############################################")

    print(captions)
    print("##############################################")

    channel_resp = medialive.create_channel(
        Name=channel_name,
        RoleArn=arn,
        LogLevel='DEBUG',
        InputAttachments=[{
            'InputId': input_id,
            "InputSettings": {
                "AudioSelectors": [],
                "CaptionSelectors": [
                    {
                        "Name": "EmbeddedSelector",
                        "SelectorSettings": {
                            "EmbeddedSourceSettings": {
                                "Convert608To708": "DISABLED",
                                "Scte20Detection": "OFF",
                                "Source608ChannelNumber": 1,
                                "Source608TrackNumber": 1
                            }
                        }
                    }
                ],
                "DeblockFilter": "DISABLED",
                "DenoiseFilter": "DISABLED",
                "FilterStrength": 1,
                "InputFilter": "AUTO",
                "NetworkInputSettings": {
                    "ServerValidation": "CHECK_CRYPTOGRAPHY_AND_VALIDATE_NAME"
                },
                "SourceEndBehavior": "CONTINUE"
            }
        }],
        Destinations=[{
            'Id': 'destination1',
            'Settings': [
                {'Url': destinations[0]['Url'], 'Username': destinations[0]['Username'],
                    'PasswordParam': destinations[0]['Password']},
                {'Url': destinations[1]['Url'], 'Username': destinations[1]['Username'],
                    'PasswordParam': destinations[1]['Password']},

            ]
        }],
        EncoderSettings={
            'AudioDescriptions': audio_descriptions,
            'CaptionDescriptions': captions,
            'OutputGroups': [
                {
                    "OutputGroupSettings": {
                        "HlsGroupSettings": {
                            "AdMarkers": [
                                "ELEMENTAL_SCTE35"
                            ],
                            "CaptionLanguageMappings": [
                                {
                                    "CaptionChannel": 1,
                                    "LanguageCode": "eng",
                                    "LanguageDescription": "english"
                                }
                            ],
                            "CaptionLanguageSetting": "INSERT",
                            "ClientCache": "ENABLED",
                            "CodecSpecification": "RFC_4281",
                            "Destination": {
                                "DestinationRefId": "destination1"
                            },
                            "DirectoryStructure": "SINGLE_DIRECTORY",
                            "HlsCdnSettings": {
                                "HlsWebdavSettings": {
                                    "ConnectionRetryInterval": 1,
                                    "FilecacheDuration": 300,
                                    "HttpTransferMode": "NON_CHUNKED",
                                    "NumRetries": 10,
                                    "RestartDelay": 15
                                }
                            },
                            "IndexNSegments": 10,
                            "InputLossAction": "PAUSE_OUTPUT",
                            "IvInManifest": "INCLUDE",
                            "IvSource": "FOLLOWS_SEGMENT_NUMBER",
                            "KeepSegments": 21,
                            "ManifestCompression": "NONE",
                            "ManifestDurationFormat": "FLOATING_POINT",
                            "Mode": "LIVE",
                            "OutputSelection": "MANIFESTS_AND_SEGMENTS",
                            "ProgramDateTime": "EXCLUDE",
                            "ProgramDateTimePeriod": 600,
                            "RedundantManifest": "DISABLED",
                            "SegmentLength": 6,
                            "SegmentationMode": "USE_SEGMENT_DURATION",
                            "SegmentsPerSubdirectory": 10000,
                            "StreamInfResolution": "INCLUDE",
                            "TimedMetadataId3Frame": "PRIV",
                            "TimedMetadataId3Period": 10,
                            "TsFileMode": "SEGMENTED_FILES"
                        }
                    },
                    'Name': 'HD',
                    'Outputs': outputs
                }
            ],
            'TimecodeConfig': {
                'Source': 'EMBEDDED'
            },
            'VideoDescriptions': video_descriptions
        }
    )
    return channel_resp
    # return 'true'


