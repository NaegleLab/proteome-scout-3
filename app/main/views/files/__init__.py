from flask import Blueprint

bp = Blueprint('compendia', __name__,
    template_folder='templates',
    static_folder='static')

from app.main.views.files import compendia
