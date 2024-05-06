from flask import render_template, redirect, flash, url_for, request
from flask_login import login_required, logout_user, current_user, login_user
from app.utils.email import send_password_reset_email
from app.main.forms.email_validator import EmailForm
from app import current_app
import sqlalchemy as sa
from app.database.user import User, load_user_by_username, load_user_by_email#, send_password_reset_email
from app.main.forms import email_validator
from app.main.views.experiments import bp
from app.utils.email import send_email
from app import db


# creating temp function for data exports
@bp.route('/experiment/download_experiment/<int:experiment_id>')
def download_experiment(experiment_id):
    form = EmailForm()
    if form.validate_on_submit(): 
        send_email('test', sender = current_app.config['ADMINS'][0], recipients = [form.email.data], text_body = 'test', html_body = 'test')
        
        


    # Fetch the experiment data using experiment_id
    # Render a template or return a response
    return render_template('proteomescout/experiments/download_experiment.html', experiment_id=experiment_id, form=form)