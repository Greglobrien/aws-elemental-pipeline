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
import re
import time
import sys

def send(event, context, responseStatus, responseData, physicalResourceId):
    responseUrl = event['ResponseURL']

    responseBody = {
        'Status': responseStatus,
        'Reason': 'See the details in CloudWatch Log Stream: ' + context.log_stream_name,
        'PhysicalResourceId': physicalResourceId or context.log_stream_name,
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'Data': responseData
    }

    json_responseBody = json.dumps(responseBody)

    print("Response body:\n" + json_responseBody)

    headers = {
        'content-type': '',
        'content-length': str(len(json_responseBody))
    }

    try:
        response = requests.put(responseUrl,
                                data=json_responseBody,
                                headers=headers)
        print("Status code: " + response.reason)
    except Exception as e:
        print("send(..) failed executing requests.put(..): " + str(e))

    return


def debug(message):
    #if event['Debug'] == "ON":
    print(('----->  %s') % str(message))
    print('######################################################\n')

def stack_name(event):
    try:
        response = event['ResourceProperties']['StackName']
    except Exception:
        response = None
    return response


def wait_for_channel_states(medialive, channel_id, states):
    current_state = ''
    while current_state not in states:
        time.sleep(5)
        current_state = medialive.describe_channel(
            ChannelId=channel_id)['State']
    return current_state


def wait_for_input_states(medialive, input_id, states):
    current_state = ''
    while current_state not in states:
        time.sleep(5)
        current_state = medialive.describe_input(InputId=input_id)['State']
    return current_state


def ssm_a_password(event, mp_channel):
    ssm = boto3.client('ssm')
    if event["RequestType"] == "Create":
        for index, key in enumerate(mp_channel["Data"]["HlsIngest"]["IngestEndpoints"]):
            response = ssm.put_parameter(
                Name='/medialive/%s-%s-%s'% (event['ResourceProperties']['StackName'], event["LogicalResourceId"], index),
                Description='{}'.format(event["LogicalResourceId"]),
                Value='{}'.format(mp_channel["Data"]["HlsIngest"]["IngestEndpoints"][index]["Password"]),
                Type='SecureString',
                KeyId='alias/aws/ssm',
                Overwrite=True
            )
            debug("SSM_a_Password: %s " % response)
            print(index, key)

            if (index == 1) and (response['ResponseMetadata']['HTTPStatusCode'] == 200):
                result = {
                    'Status': 'SUCCESS',
                    'Data': {
                        'PackagerPrimaryChannelPassword': '/medialive/%s-%s-0' % (event['ResourceProperties']['StackName'], event["LogicalResourceId"]),
                        'PackagerSecondaryChannelPassword':'/medialive/%s-%s-1' % (event['ResourceProperties']['StackName'], event["LogicalResourceId"])
                    }
                }
    if event["RequestType"] == "Delete":
        result = ssm.delete_parameters(
            Names=[
                event["ResourceProperties"]["PackagerPrimaryChannelPassword"],
                event["ResourceProperties"]["PackagerSecondaryChannelPassword"]
            ]
        )

    return result


def does_exist(event, context):
    channel_id = '%s-%s'% (event['ResourceProperties']['StackName'], event["LogicalResourceId"])
    client = boto3.client('medialive')
    channel_list = client.list_channels()
    for channel in channel_list['Channels']:
        # print("Channel: %s\n" % channel)
        if (channel_id == channel['Name']):
            sys.exit("Cannot Overwrite existing Channel!")

    return False

