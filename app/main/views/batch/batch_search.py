from turtle import title
from app.config import strings
from flask import render_template, redirect, request, url_for
from flask_login import current_user
from app.main.views.batch import bp
from app.main.forms.batch_search_form import BatchSearchForm



@bp.route('/', methods=['GET', 'POST'])
def batch_search():
    form = BatchSearchForm()
    user = current_user if current_user.is_authenticated else None

    if form.validate_on_submit():
        
        return render_template('proteomescout/info/information.html',
        title = strings.protein_batch_search_submitted_page_title,
        header = strings.protein_batch_search_submitted_page_title,
        message = strings.protein_batch_search_submitted_message,
        link = url_for('info.home'),
        )
    else:
        return render_template(
        'proteomescout/batch/batch_search.html',
        title = strings.protein_batch_search_page_title,
        form = form,
        )


