from turtle import title
from app.config import strings
from flask import render_template, redirect, request, url_for
from flask_login import current_user
from app.main.views.batch import bp
from app.main.forms.batch_search_form import BatchSearchForm
from app.database import jobs
import time
from random import randint
from proteomescout_worker import export_tasks

def create_job_and_submit(accessions, user_id):
    #accessions = accessions.split()
    accessions = accessions.replace(',', ' ').split()
    batch_id = "%f.%d" % (time.time(), randint(0,10000))

    j = jobs.Job()
    j.status = 'in queue'
    j.stage = 'initializing'
    j.progress = 0
    j.max_progress = 0
    j.status_url = url_for('account.manage_experiments')
    # placeholder
    j.result_url = url_for('info.home')
    # j.result_url = request.route_url('batch.batch_download', id=batch_id)
    if len(accessions) == 1:
        j.name = "Batch annotate 1 protein"
    else:
        j.name = "Batch annotate %d proteins" % (len(accessions))
    j.type = 'batch_annotate'
    j.user_id = user_id
    j.save()

    export_tasks.batch_annotate_proteins.apply_async((accessions, batch_id, user_id, j.id))


@bp.route('/', methods=['GET', 'POST'])
def batch_search():
    form = BatchSearchForm()
    user = current_user if current_user.is_authenticated else None

    if form.validate_on_submit():
        accessions = form.accessions.data

        create_job_and_submit(accessions, user.id)
        return render_template('proteomescout/info/information.html',
        title = strings.protein_batch_search_submitted_page_title,
        header = strings.protein_batch_search_submitted_page_title,
        message = strings.protein_batch_search_submitted_message,
        link = url_for('account.manage_experiments'),
        )
    else:
        return render_template(
        'proteomescout/batch/batch_search.html',
        title = strings.protein_batch_search_page_title,
        form = form,
        )


