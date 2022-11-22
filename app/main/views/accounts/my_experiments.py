from app.main.views.accounts import bp
from flask import render_template, redirect, url_for, request
from flask_login import current_user

@bp.route('/experiments', methods=['GET', 'POST'])
def manage_experiments():
    return render_template('proteomescout/accounts/my_experiments.html')