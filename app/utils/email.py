from flask_mail import Message
from app import mail, celery
from flask import render_template
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