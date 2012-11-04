# pylint: disable-msg=C0103
# pylint: enable-msg=C0103
# tempfile regex format
#
# pylint: disable-msg=C0111
# missing docstring
#
# pylint: disable-msg=W0232
# no __init__ method
#
# pylint: disable-msg=R0903
# to few public methods
#
# DISABLED_ylint: disable-msg=R0201
# method could be a function
#
#!/usr/bin/python
# -*- coding: utf-8 -*-

import smtplib
import os
import re
import mimetypes
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import utils, encoders
from django.conf import settings
from BeautifulSoup import UnicodeDammit

# pylint: disable-msg=F0401

import settings
import html2text

# pylint: enable-msg=F0401

def determine_encoding(text):
    possible_charsets = ["US-ASCII", "ISO-8859-1", "UTF-8"]
    for charset in possible_charsets:
        try:
            text.encode(charset)
        except UnicodeError:
            pass
        else:
            return charset
    error_msg = "Unable to determine the correct encoding. Please ensure that a encoding into one of %s is possible." % (possible_charsets, )
    raise Exception(error_msg)


def create_message_container(em_from, em_to, em_reply_to):
    from_hdr = (utils.formataddr((em_from.name, em_from.email)) if len(em_from.name) > 0 else utils.formataddr((False, em_from.email)))
    reply_to_hdr = (utils.formataddr((em_reply_to.name, em_reply_to.email)) if len(em_reply_to.name) > 0 else utils.formataddr((False,
                    em_reply_to.name)))
    to_hdr = (utils.formataddr((em_to.name, em_to.email)) if len(em_to.name) > 0 else utils.formataddr((False, em_to.name)))
    from_hdr_charset = determine_encoding(from_hdr)
    reply_to_hdr_charset = determine_encoding(reply_to_hdr)
    to_hdr_charset = determine_encoding(to_hdr)

    # Create message container - This one will house the 'multipart alternative part'
    # and the 'attachments part'.

    mime_mulitpart_mixed = MIMEMultipart("mixed")
    mime_mulitpart_mixed["From"] = Header(from_hdr.encode(from_hdr_charset), from_hdr_charset)
    mime_mulitpart_mixed["To"] = Header(to_hdr.encode(to_hdr_charset), to_hdr_charset)
    mime_mulitpart_mixed["Date"] = Header(utils.formatdate())
    mime_mulitpart_mixed["Reply-To"] = Header(reply_to_hdr.encode(reply_to_hdr_charset), reply_to_hdr_charset)
    mime_mulitpart_mixed["Precedence"] = Header("junk", "US-ASCII")
    mime_mulitpart_mixed["Auto-Submitted"] = Header("auto-generated", "US-ASCII")
    return mime_mulitpart_mixed


def create_mime_multipart_msg(plain_body, html_body):
    html_body_charset = determine_encoding(html_body)
    plain_body_charset = determine_encoding(plain_body)

    # Create message container - the correct MIME type is multipart/alternative.
    # This will house the HTML and Plain Text body

    mime_multipart_msg = MIMEMultipart("alternative")

    # Record the MIME types of both parts - text/plain and text/html.

    part1 = MIMEText(plain_body.encode(plain_body_charset), "plain", plain_body_charset)
    part2 = MIMEText(html_body.encode(html_body_charset), "html", html_body_charset)

    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.

    mime_multipart_msg.attach(part1)
    mime_multipart_msg.attach(part2)
    return mime_multipart_msg


def add_attachments(mime_mulitpart_mixed, attachments):
    for file_name in attachments:
        if not os.path.isfile(file_name):
            continue
        (ctype, encoding) = mimetypes.guess_type(file_name)
        if ctype is None or encoding is not None:

            # No guess could be made, or the file is encoded (compressed), so
            # use a generic bag-of-bits type.

            ctype = "application/octet-stream"
        (maintype, subtype) = ctype.split("/", 1)
        if maintype == "text":
            file_pointer = open(file_name)
            content = UnicodeDammit(file_pointer.read())
            content_charset = determine_encoding(content.unicode)
            content = content.unicode.encode(content_charset)
            parta = MIMEText(content, _subtype=subtype, _charset=content_charset)
            file_pointer.close()
        elif maintype == "image":
            file_pointer = open(file_name, "rb")
            parta = MIMEImage(file_pointer.read(), _subtype=subtype)
            file_pointer.close()
        elif maintype == "audio":
            file_pointer = open(file_name, "rb")
            parta = MIMEAudio(file_pointer.read(), _subtype=subtype)
            file_pointer.close()
        else:
            file_pointer = open(file_name, "rb")
            parta = MIMEBase(maintype, subtype)
            parta.set_payload(file_pointer.read())
            file_pointer.close()

            # Encode the payload using Base64

            encoders.encode_base64(parta)

        # Set the filename parameter

        parta.add_header("Content-Disposition", "attachment; filename=%s" % os.path.basename(file_name))
        mime_mulitpart_mixed.attach(parta)
    return mime_mulitpart_mixed


def send_message(from_email, to_list, mime_multipart_mixed_message):
    result = {}
    mta = smtplib.SMTP(settings.EMAIL_HOST)
    mta.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
    try:
        result = mta.sendmail(from_email, to_list, mime_multipart_mixed_message.as_string())
    except smtplib.SMTPRecipientsRefused, exc:
        result = exc.recipients
    except smtplib.SMTPException, exc:
        for email in to_list:
            result[email] = str(exc)
    except Exception, exc:
        for email in to_list:
            result[email] = str(exc)
    try:
        mta.quit()
    except smtplib.SMTPException, exc:
        pass
    return result


def gen_mime_message(header, body, attachments):

    from_hdr = header.from_obj
    to_hdr = header.to_obj
    reply_hdr = header.reply_obj
    subject = header.get_subject()

    # create the mimeobject with the headers, and recipiants

    message_container = create_message_container(from_hdr, to_hdr, reply_hdr)

    # create mimeobject with the html and plain text

    plain_body = body.txt
    html_body = body.html
    mime_multipart_msg = create_mime_multipart_msg(plain_body, html_body)

    # attache the mesage (with html and plain text) to the message container

    message_container.attach(mime_multipart_msg)

    # add the attachments

    message_container = add_attachments(message_container, attachments)

    # set the subject

    subject_charset = determine_encoding(subject)
    message_container["Subject"] = Header(subject.encode(subject_charset), subject_charset)

    return message_container


# too many arguments
# pylint: disable-msg=R0913
#
# invalid name
# pylint: disable-msg=C0103
#
# too many local variiables
# pylint: disable-msg=R0914

def GenerateMessage(
    from_name,
    from_email,
    reply_to_name,
    reply_to_email,
    to_name,
    to_email,
    subject,
    html_body,
    plain_body,
    attachments,
    ):

    from_hdr = EmailName(from_email, from_name)
    to_hdr = EmailName(to_email, to_name)
    reply_hdr = EmailName(reply_to_email, reply_to_name)

    # create the mimeobject with the headers, and recipiants

    message_container = create_message_container(from_hdr, to_hdr, reply_hdr)

    # create mimeobject with the html and plain text

    mime_multipart_msg = create_mime_multipart_msg(plain_body, html_body)

    # attache the mesage (with html and plain text) to the message container

    message_container.attach(mime_multipart_msg)

    # add the attachments

    message_container = add_attachments(message_container, attachments)

    # set the subject

    subject_charset = determine_encoding(subject)
    message_container["Subject"] = Header(subject.encode(subject_charset), subject_charset)

    return message_container


def SendMessage(from_email, to_list, msg):
    return send_message(from_email, to_list, msg)


# pylint: enable-msg=R0913
# pylint: enable-msg=C0103
# pylint: enable-msg=R0914

class EmailName:
    name = None
    email = None
    def __repr__(self):
        return self.name + " <" + self.email + ">"
    def __init__(self, email, name=None):
        email_pattern = \
            re.compile("(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*|^\"([\\001-\\010\\013\\014\\016-\\037!#-\\[\\]-\\177]|\\\\  "
                       "                     [\\001-011\\013\\014\\016-\\177])*\")@(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\\.)+[A-Z]{2,6}\\.?$",
                       re.IGNORECASE)  # dot-atom

                                         # quoted-string

        if not email_pattern.match(email):
            raise Exception("This is not a valid email address -> " + str(email))
        if not name:
            self.name = email
        else:
            self.name = name
        self.email = email


class EmailHeader(object):

    def __init__(
        self,
        subject,
        from_obj,
        to_obj,
        reply_obj,
        ):

        self._subject = subject
        self._from_obj = from_obj
        self._to_obj = to_obj
        self._reply_obj = reply_obj


    def set_subject(self, value):
        self._subject = value

    def get_subject(self):
        if not self._subject:
            return ""
        return self._subject

    subject = property(get_subject, set_subject)

    def get_from_obj(self):
        if not self._from_obj:
            raise Exception("from_obj is not set")
        return self._from_obj

    from_obj = property(get_from_obj)

    def get_to_obj(self):
        if not self._to_obj:
            raise Exception("to_obj is not set")
        return self._to_obj

    to_obj = property(get_to_obj)

    def get_reply_obj(self):
        if not self._reply_obj:
            raise Exception("reply_obj is not set")
        return self._reply_obj

    reply_obj = property(get_reply_obj)


class Body(object):
    _txt = None
    _html = None

    def __init__(self, html, txt=None):
        self.html = html
        self.txt = txt

    def set_txt(self, value):
        self._txt = value

    def get_txt(self):
        if not self._txt:
            return str(html2text.html2text(self.html))
        return self._txt

    txt = property(get_txt, set_txt)

    def set_html(self, value):
        self._html = value

    def get_html(self):
        return self._html

    html = property(get_html, set_html)

# too many instance variables
# pylint: disable-msg=R0902

class Email(object):

    def __init__(self):
        self._attachments = []
        self._body = None
        self._to_email = None
        self._reply_email = None
        self._subject = None

    def set_subject(self, value):
        self._subject = value

    def get_subject(self):
        if not self._subject:
            raise Exception("subject has not been set")
        return self._subject

    subject = property(get_subject, set_subject)

    def set_body(self, value):
        if type(value)!=Body:
            raise Exception("body has to be of type Body")
        self._body = value

    def get_body(self):
        if not self._body:
            raise Exception("body has not been set")
        return self._body

    body = property(get_body, set_body)

    def set_to_email(self, email):
        self._to_email = []
        if type(email)==type(tuple()):
            value = EmailName(email[0], email[1])
        else:
            value = EmailName(email, email)
        self._to_email.append(value)

    def get_to_email(self):
        if self._to_email:
            return self._to_email[0]
        raise Exception("to_email is not set")

    to_email = property(get_to_email, set_to_email)

    def set_extra_address(self, email):
        if type(email)==type(list()):
            emails = email
            for email in emails:
                value = EmailName(email, email)
                self._to_email.append(value)
        else:
            value = EmailName(email, email)
        self._to_email.append(value)
    extra_address = property(None, set_extra_address)

    def set_reply_email(self, email):
        if type(email)==type(tuple()):
            value = EmailName(email[0], email[1])
        else:
            value = EmailName(email, email)
        self._reply_email = value

    def get_reply_email(self):
        return self._reply_email

    reply_email = property(get_reply_email, set_reply_email)

    def set_attachments(self, value):
        self._attachments = value

    def get_attachments(self):
        if not self._attachments:
            return []
        return self._attachments

    attachments = property(get_attachments, set_attachments)

    def get_recipient_list(self):
        email_list = [x.email for x in self._to_email]
        return list(set(email_list))

    def send(self):
        if not self.to_email:
            raise Exception("The to_email property has not been set")

        from_obj = EmailName(settings.EMAIL_FROM_EMAIL, settings.EMAIL_FROM)

        if not self.reply_email:
            self.reply_email = (settings.EMAIL_FROM_EMAIL, settings.EMAIL_FROM)
        else:
            from_obj = EmailName(settings.EMAIL_FROM_EMAIL, self._reply_email.name)

        header = EmailHeader(self._subject, from_obj, self.to_email, self.reply_email)

        message = gen_mime_message(header, self.body, self.attachments)

        return send_message(from_obj, self.get_recipient_list(), message)
# pylint: enable-msg=R0902

def send_test_message_old_style():
    subject = "Refactored mailer"
    ascii = "Dit mailtje is gestuurd met de mailer die attached is."
    html = "<HTML><HEAD></HEAD><BODY><P STYLE=\"font-size: 14px; font-family: 'Courier New', Courier, monospace;\"><b>" + ascii.replace(" ", "&nbsp;"
            ).replace("\n", "<br/>\n") + "</b></p></BODY></HTML>"
    msg = GenerateMessage(
        "Active8 Mail test",
        "reply_project@active8.nl",
        "Active8",
        "reply_project@active8.nl",
        "Active8 Reply to",
        "info@a8.nl",
        subject,
        html,
        ascii,
        ["mailer.py"],
        )
    SendMessage("reply_project@active8.nl", ["erik@a8.nl"], msg)


def send_test_message_new_style():

    email = Email()
    email.reply_email = ("rene@a8.nl", "Rene van Hoek")
    email.to_email = ("erik@a8.nl", "Erik de Jonge")
    email.subject = "Hello world subject?"
    email.body = Body("<html><head><title>hello</title></head><body><b>hello world</b><br/><i>en dit is italic</i></body></html>")
    email.send()

def main():
    pass


# to_email = EmailName("erik@a8.nl", "Erik de Jonge")
# simple_email(to_email, "Mijn onderwep", "Dit is <b>html</b> tekst")

if __name__ == "__main__":
    from django.core.management import setup_environ
    setup_environ(settings)
    main()

    send_test_message_new_style()
