from app.main.views.info import bp
from flask import render_template
@bp.route('/')
def home():
    return render_template('proteomescout/landing/landing.html')