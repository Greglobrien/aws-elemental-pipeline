# aws-elemental-pipeline
Credit where credit is due, this is based off the AWS Sample: https://github.com/aws-samples/aws-media-services-simple-live-workflow

The AWS Sample is designed to run on cloudformation, whereas this version can be run from you machine, all you need is Boto3 and your AWS Credentials.

It builds a pipeline that looks like this: 

###Elemental MediaLive -> Elemental MediaPackage -> Elemental MediaTailor

To run this tool simply update the demo json and run the program by adding it as an arguement `$ python main.py demo.json` the python will do the rest.

Still a lot of work to do on this, including building out the pipeline with MediaStore in place of MediaPackage, so check back from time to time.