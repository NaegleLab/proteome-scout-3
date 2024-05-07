from flask_mail import Message
from app import mail, celery
from flask import render_template
from app import current_app
import os 
from app import current_app 


def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    mail.send(msg)




# ...

def send_password_reset_email(user):
    token = user.get_reset_password_token()
    send_email('[Proteomescout] Reset Your Password',
               sender= current_app.config['ADMINS'][0], #config['MAIL_USERNAME'],
               recipients=[user.email],
               text_body=render_template('proteomescout/email/reset_password.txt',
                                         user=user, token=token),
               html_body=render_template('proteomescout/email/reset_password.html',
                                         user=user, token=token))
    

# Making function to send email and registering as a celery task 

@celery.task
def send_email_with_exp_download(recipient, subject, body, attachment_path):
    #sender = current_app.config['ADMINS'][0]
    sender = "ProteomeScout <{}>".format(current_app.config['ADMINS'][0])
    msg = Message(subject, recipients=[recipient], sender = sender)
    msg.body = body

    with open(attachment_path, "rb") as fp:
        msg.attach(
            filename=os.path.basename(attachment_path),
            content_type="text/csv",
            data=fp.read(),
        )

    mail.send(msg)