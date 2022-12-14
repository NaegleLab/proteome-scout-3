import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
import os
from flask import Flask, request, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from .celery_utils import init_celery
# from . import flask_celery
# from flask_mail import Mail
# from flask_bootstrap import Bootstrap
# from flask_moment import Moment
# from flask_babel import Babel, lazy_gettext as _l
# from elasticsearch import Elasticsearch
# from redis import Redis
# import rq
from config import Config
from celery import Celery


access_key = Config.CELERY_ACCESS_KEY
secret_key = Config.CELERY_SECRET_ACCESS_KEY
queue_url = Config.QUEUE_URL
broker_transport_options = {
    'predefined_queues': {
        'celery': {
            'url': queue_url,
            'access_key_id': access_key,
            'secret_access_key': secret_key,
        }
    }
}
def make_celery(app_name=__name__):
    result_backend = Config.result_backend
    broker_url = Config.CELERY_BROKER_URL
    celery = Celery(app_name, backend=result_backend, broker=broker_url, )
    return celery

celery = make_celery()
celery.conf['broker_transport_options']=broker_transport_options
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = 'Please log in to access this page.'

def create_app(config_class=Config, celery=celery):
    app = Flask(__name__)
    app.config.from_object(config_class)

    init_celery(celery, app)
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    # mail.init_app(app)
    # bootstrap.init_app(app)
    # moment.init_app(app)
    # babel.init_app(app)
    # app.elasticsearch = Elasticsearch([app.config['ELASTICSEARCH_URL']]) \
    #     if app.config['ELASTICSEARCH_URL'] else None
    # app.redis = Redis.from_url(app.config['REDIS_URL'])
    # app.task_queue = rq.Queue('proteomescout-tasks', connection=app.redis)

    

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.main.views.info import bp as info_bp
    app.register_blueprint(info_bp)

    from app.main.views.accounts import bp as accounts_bp
    app.register_blueprint(accounts_bp, url_prefix='/account')

    from app.main.views.proteins import bp as protein_bp
    app.register_blueprint(protein_bp, url_prefix = '/proteins')

    from app.main.views.batch import bp as batch_bp
    app.register_blueprint(batch_bp, url_prefix = '/batch')

    from app.main.views.experiments import bp as exp_bp
    app.register_blueprint(exp_bp, url_prefix = '/experiments')

    from app.main.views.upload import bp as upload_bp
    app.register_blueprint(upload_bp, url_prefix = "/upload")

    # from app.api import bp as api_bp
    # app.register_blueprint(api_bp, url_prefix='/api')

    if not app.debug and not app.testing:
        if app.config['MAIL_SERVER']:
            auth = None
            if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
                auth = (app.config['MAIL_USERNAME'],
                        app.config['MAIL_PASSWORD'])
            secure = None
            if app.config['MAIL_USE_TLS']:
                secure = ()
            mail_handler = SMTPHandler(
                mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
                fromaddr='no-reply@' + app.config['MAIL_SERVER'],
                toaddrs=app.config['ADMINS'], subject='Microblog Failure',
                credentials=auth, secure=secure)
            mail_handler.setLevel(logging.ERROR)
            app.logger.addHandler(mail_handler)

        if app.config['LOG_TO_STDOUT']:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.INFO)
            app.logger.addHandler(stream_handler)
        else:
            if not os.path.exists('logs'):
                os.mkdir('logs')
            file_handler = RotatingFileHandler('logs/proteomescout.log',
                                               maxBytes=10240, backupCount=10)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s '
                '[in %(pathname)s:%(lineno)d]'))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Proteomescout startup')

    return app

app = create_app()

# mail = Mail()
# bootstrap = Bootstrap()
# moment = Moment()
# babel = Babel()



# @celery.task
# def add(x, y):
#     return x+y

# @babel.localeselector
# def get_locale():
#     return request.accept_languages.best_match(current_app.config['LANGUAGES'])

from proteomescout_worker import notify_tasks

from app.database import user