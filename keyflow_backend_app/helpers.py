from math import e
import os
import random
import string
from dotenv import load_dotenv
import boto3
from django.core.files.storage import default_storage
import sendgrid
import os
from sendgrid.helpers.mail import Mail, Email, To, Content
from sendgrid import SendGridAPIClient
load_dotenv()


def make_id(length):
    result = ""
    characters = string.ascii_letters + string.digits
    characters_length = len(characters)
    counter = 0
    while counter < length:
        result += characters[random.randint(0, characters_length - 1)]
        counter += 1
    return result


def strtobool(val):
    """Convert a string representation of truth to true (1) or false (0).
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif val in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        raise ValueError("invalid truth value %r" % (val,))


# Function to generate a presigned URL for a specific S3 file
def generate_presigned_url(file_key):
    s3_client = boto3.client("s3", region_name=os.getenv("AWS_S3_REGION_NAME"))

    # Generate a presigned URL for the file_key within your S3 bucket
    presigned_url = s3_client.generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": os.getenv("AWS_STORAGE_BUCKET_NAME"),
            "Key": file_key,
        },
        ExpiresIn=3600,  # Optional: URL expiration time in seconds
    )

    return presigned_url


def sendEmailBySendGrid(from_email, to_email, subject, content, is_html=False):
    api_key = os.getenv("SENDGRID_API_KEY")
    sg = sendgrid.SendGridAPIClient(api_key=api_key)
    from_email = Email(from_email)  # Change to your verified sender
    if os.getenv("ENVIRONMENT") == "development":
        to_email = "keyflowsoftware@gmail.com"
    to_emails = To(to_email)  # Change to your recipient
    # Check if content is html
    if is_html:
        content = Content("text/html", content)
        mail = Mail(
            from_email=from_email,
            to_emails=to_emails,
            subject=subject,
            html_content=content
        )
    else:
        content = Content("text/plain", content)
        mail = Mail(
            from_email=from_email,
            to_emails=to_emails,
            subject=subject,
            html_content=content
        )

    try:
        # Send an HTTP POST request to /mail/send
        response = sg.send(mail)
        print(response.status_code)
        print(response.headers)
        print(response.body)
        return response
    except Exception as e:
        print(e)


#Test Integration  SendGrid API KEy: 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
def sendGridTestIntegreation():
    message = Mail(
    from_email='from_email@example.com',
    to_emails='to@example.com',
    subject='Sending with Twilio SendGrid is Fun',
    html_content='<strong>and easy to do anywhere, even with Python</strong>')
    try:
        sg = SendGridAPIClient("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")
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e)