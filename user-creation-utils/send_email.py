"""Send emails via mail server"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_welcome_email(personal_email, user_id):
    """
    Sends a welcome email from the ./email/message.txt and ./email/message.html files

    :param personal_email: Personal email address to send mail to
    :type personal_email: str
    :param user_id: User ID to be formatted into message body
    :type user_id: str
    """
    with open('./email/message.txt', encoding='UTF-8') as email_txt_file:
        email_txt = email_txt_file.read()
        email_txt = email_txt.format(user_id)

    with open('./email/message.html', encoding='UTF-8') as email_html_file:
        email_html = email_html_file.read()
        email_html = email_html.format(user_id)

    mailserver_send_email('Your Account Has Been Created', email_txt, email_html,
                            'it@example.com', personal_email)

def mailserver_send_email(subject, body_plaintext, body_html, sender, recipient):
    """
    Send an email via mail server

    :param subject: Subject line
    :type subject: str
    :param body_plaintext: Message body, in plain text
    :type body_plaintext: str
    :param body_html: Message body, optionally formatted with HTML
    :type body_html: str
    :param sender: Message sender
    :type sender: str
    :param recipient: Message recipient
    :type recipient: str
    :return: True if message was sent, False if there was an exception
    :rtype: bool
    """
    HOST = 'mailserver.example.com'
    PORT = 25

    # Build email
    message = MIMEMultipart('alternative')
    message['Subject'] = subject
    message['From'] = sender
    message['To'] = recipient
    message.attach(MIMEText(body_plaintext, 'plain'))
    message.attach(MIMEText(body_html, 'html'))

    # Send email
    try:
        server = smtplib.SMTP(HOST, PORT)
        server.sendmail(sender, recipient, message.as_string())
    except Exception as _:
        return False
    return True
