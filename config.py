import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['your-email@example.com']
    LANGUAGES = ['en', 'es']
    MS_TRANSLATOR_KEY = os.environ.get('MS_TRANSLATOR_KEY')
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://'
    POSTS_PER_PAGE = 25
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL')
    result_backend = os.environ.get('CELERY_RESULT_BACKEND')
    QUEUE_URL = os.environ.get('QUEUE_URL')
    CELERY_ACCESS_KEY = os.environ.get('CELERY_ACCESS_KEY')
    CELERY_SECRET_ACCESS_KEY = os.environ.get('CELERY_SECRET_ACCESS_KEY')

    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or '/Users/bj8th/Documents/GitHub/ProteomeScout-3/flask-proteomescout/proteomescout/app/upload'
   