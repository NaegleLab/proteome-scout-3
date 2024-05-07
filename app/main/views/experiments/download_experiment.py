from flask import render_template, redirect, flash, url_for, request
from flask_login import login_required, logout_user, current_user, login_user
from app.main.forms.email_validator import EmailForm
from app import current_app
import sqlalchemy as sa
from app.database.user import User, load_user_by_username, load_user_by_email#, send_password_reset_email
from app.database import jobs 
from proteomescout_worker import export_tasks
from app.main.forms import email_validator
from app.main.forms.email_validator import EmailForm, DownloadForm
from app.main.views.experiments import bp
from app.utils.email import send_email
from app import db
import time
from random import randint




# creating temp function for data exports
#@bp.route('/experiment/download_experiment/<int:experiment_id>', methods = ['GET', 'POST'])
#def download_experiment(experiment_id):
   # form = EmailForm()
 #  if form.validate_on_submit(): 
  #      send_email('test', sender = current_app.config['ADMINS'][0], recipients = [form.email.data], text_body = 'test', html_body = 'test')
  #      flash('Email sent to ' + form.email.data)

    # Fetch the experiment data using experiment_id
    # Render a template or return a response
 #   return render_template('proteomescout/experiments/download_experiment.html', experiment_id=experiment_id, form=form)'''





def create_export_job(export_id, experiment_id, user_id):
    export_id = "%f.%d" % (time.time(), randint(0,10000))
    j = jobs.Job()
    j.status = 'in queue'
    j.stage = 'initializing'
    j.progress = 0
    j.max_progress = 0
    j.name = "Export experiment %d" % (experiment_id)
    #j.status_url = url_for('account.manage_experiments')
    # placeholder
    #j.result_url = url_for('info.home')
    # j.result_url = request.route_url('batch.batch_download', id=batch_id)
    j.type = 'experiment_export'
    j.user_id = user_id
    j.save()
    return j.id


@bp.route('/experiment/download_experiment/<int:experiment_id>', methods = ['GET', 'POST'])
def download_experiment(experiment_id):
    form = DownloadForm()
    if form.validate_on_submit(): 
        annotate = form.annotate.data
        user_id = form.email.data  # assuming user_id is email in this context

        export_id = "%f.%d" % (time.time(), randint(0,10000))
        job_id = create_export_job(export_id, experiment_id, user_id)  # replace with your actual job creation logic

        export_tasks.run_experiment_export_job.apply_async(
            args=(annotate, export_id, experiment_id, user_id, job_id),
        )
        flash('Export job started. You will receive an email when it is complete.')

    return render_template('proteomescout/experiments/download_experiment.html', experiment_id=experiment_id, form=form)