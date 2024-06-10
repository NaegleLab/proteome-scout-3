from turtle import title
from app.config import strings
from flask import render_template, redirect, request, url_for, flash , send_from_directory
from flask_login import current_user
from app.main.views.batch import bp
from app.main.forms.batch_search_form import BatchSearchForm
from app.database import jobs
import time
from random import randint
from proteomescout_worker import export_tasks
import os 

def create_job_and_submit(accessions, user_id):
    accessions = accessions.replace(',', ' ').split()
    batch_id = "%f.%d" % (time.time(), randint(0,10000))

    j = jobs.Job()
    j.status = 'in queue'
    j.stage = 'initializing'
    j.progress = 0
    j.max_progress = 0
    j.status_url = url_for('account.manage_experiments')

    if len(accessions) == 1:
        j.name = "Batch annotate 1 protein"
    else:
        j.name = "Batch annotate %d proteins" % (len(accessions))
    j.type = 'batch_annotate'
    j.user_id = user_id

    # Generate the filename
    batch_filename = f"batch_{batch_id}.zip"

    # Generate the result URL
    #result_url = url_for('batch.download_result', filename=batch_filename,  _external=True)
    result_url = url_for('batch.download_result', batch_id=batch_id, user_id=current_user.id, _external=True)
    print(f"Generated URL: {result_url}")       

    # Update the job with the result_url
    j.result_url = result_url
    j.save()
    job_id = j.id
    export_tasks.batch_annotate_proteins.apply_async((accessions, batch_id, user_id, job_id))


@bp.route('/', methods=['GET', 'POST'])
def batch_search():
    form = BatchSearchForm()

    if form.validate_on_submit():
        if current_user.is_authenticated:
            accessions = form.accessions.data
            create_job_and_submit(accessions, current_user.id)
            return render_template('proteomescout/info/information.html',
                                   title=strings.protein_batch_search_submitted_page_title,
                                   header=strings.protein_batch_search_submitted_page_title,
                                   message=strings.protein_batch_search_submitted_message,
                                   link=url_for('account.manage_experiments'),
                                   )
        else:
            flash('You are not signed in. Please sign in to continue.')
            return redirect(url_for('auth.login', next=request.url))
    else:
        return render_template(
            'proteomescout/batch/batch_search.html',
            title=strings.protein_batch_search_page_title,
            form=form,
        )
        

@bp.route('/download_result/<batch_id>/<user_id>', methods=['GET'])
def download_result(batch_id, user_id):
    filename = "batch_%s_%s.zip" % (batch_id, user_id)
    file_path = os.path.join('app/data/annotate', filename)  # Construct the relative file path

    #print(os.getcwd())
    #print(os.path.exists(file_path))

    print(file_path)
    if os.path.exists(file_path):
        absolute_directory = os.path.abspath(os.path.dirname(file_path))
        return send_from_directory(absolute_directory, os.path.basename(file_path), as_attachment=True)
    else:
        return "File not found", 404


