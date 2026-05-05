import smtplib
from  email.message import EmailMessage
app_password = 'tljk ywhk lhir ehev'
SENDER = "ryomensukuna1230@gmail.com"

def send_mail(to, subject, body):
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login('ryomensukuna1230@gmail.com', app_password)
    msg = EmailMessage()
    msg['FROM'] = 'ryomensukuna1230@gmail.com'
    msg['SUBJECT'] = subject
    msg['TO'] = to
    msg.set_content(body)
    server.send_message(msg)
    server.close()
    