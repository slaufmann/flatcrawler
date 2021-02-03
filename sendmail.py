# CC0 - free software.
# To the extent possible under law, all copyright and related or neighboring
# rights to this work are waived.
"""
A simple Mail class, wrapping python's smtplib.

First, modify the MailConfig class in config.py to be able to send mail.

There are only two methods: Mail() and send().
Create and send and an email like so:

>>> Mail('recipient@example.com', 'subject', 'hello,\nthis is email.\nthanks!').send()
True

You can attach files like this:
>>> with open('attachment.png', 'rb') as f:
...     data = f.read()
... Mail(
...     'recipient@example.com',
...     'subject',
...     'hello,\nthis is email with image.\nthanks!',
...     {'different_name.png': data}
... ).send()
True

You can send blind copies (BCC) to a list of email addresses:

>>> Mail(
...     'recipient@example.com',
...     'subject',
...     'hello,\nthis is email.\nthanks!',
...     bcc=['alice@example.com', 'bob@example.com']
... ).send()

The send() function returns False if something went wrong, and errors will be
printed to stdout.

TODO: make an error field in Mail and fill that with errors instead of
printing.
"""
import sys
import time

import smtplib
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email import encoders
import yaml


class MailConfig:
    def __init__(self):
        with open("config.yaml", "r") as config_file:
            data = yaml.safe_load(config_file)
            if "mail" in data:
                yaml_data = data["mail"]
                self.server = yaml_data["server"]
                self.user = yaml_data["user"]
                self.password = yaml_data["password"]
                self.from_ = yaml_data["from"]
                self.reply_to = yaml_data["reply_to"]
                self.recipient = yaml_data["recipient"]
                self.bcc_recipients = yaml_data["bcc_recipients"]


class Mail(object):
    def __init__(self, to, subject="", text="", attachments={}, bcc=None):
        """
        Create an email.
        
        Args:
            to (str): Email address to send to
            subject (str): Email subject line
            text (str): The email text
            attachments (Mapping[string, bytes]): A filename and the content
                encoded as a bytes-sequence.
            bcc (Union[string, List[string]]): A single email address or a
                list of addresses to BCC the data to.
        """
        self.mail_config = MailConfig()

        if attachments:
            msg = MIMEMultipart()
            msg.attach(MIMEText(text))

            for name, filedata in attachments.items():
                attachment_part = MIMEBase("application", "octet-stream")
                attachment_part.set_payload(filedata)
                encoders.encode_base64(attachment_part)
                attachment_part.add_header(
                    "Content-Disposition", 'attachment; filename="{}"'.format(name)
                )
                msg.attach(attachment_part)
        else:
            msg = MIMEText(text)

        msg["Subject"] = subject
        msg["To"] = to
        msg["From"] = self.mail_config.from_
        msg["Reply-To"] = self.mail_config.reply_to
        self.email = {"address": to, "msg": msg}
        self.bcc = bcc

    def send(self, retries=3):
        """
        Send the email.
        
        Args:
            retries (int): How often to retry in case of errors. The wait time
                between tries increases quadratically in seconds. For e.g.
                retries=3 wait times would be 0s, 1s and 4s. Actual wait times
                may be much larger due to network timeouts etc.
        
        Returns:
            True on successful send, False on failure.
        """
        tries = 0
        to = [self.email["address"]]
        if self.bcc:
            try:
                to = to + self.bcc
            except TypeError:
                to += [self.bcc]
            print(to)
        if self.email["address"]:
            success = False
            while not success and tries < retries:
                try:
                    ## SMTPlib-Code from mkyong.com
                    ## http://www.mkyong.com/python/how-do-send-email-in-python-via-smtplib/
                    smtpserver = smtplib.SMTP(self.mail_config.server)
                    smtpserver.ehlo()
                    smtpserver.starttls()
                    smtpserver.ehlo()
                    smtpserver.login(self.mail_config.user, self.mail_config.password)
                    smtpserver.sendmail(
                        self.mail_config.user, to, self.email["msg"].as_string()
                    )
                except smtplib.SMTPAuthenticationError:
                    print("Failed sending: Authentication Error")
                    time.sleep(tries)
                    tries += 1
                except OSError as oe:
                    print(
                        "Failed sending to <{}> {}: {} (waiting {}s)".format(
                            self.email["address"],
                            ["once", "twice", "{} times"][min(tries, 2)].format(
                                tries + 1
                            ),
                            oe,
                            tries ** 2,
                        )
                    )
                    time.sleep(tries ** 2)
                    tries += 1
                else:
                    success = True
                finally:
                    try:
                        smtpserver.close()
                    except UnboundLocalError:
                        pass
            return success
        else:
            print("No mail adresses given, no mails sent.")
            return True

    def __str__(self):
        return self.email["msg"].as_string()
