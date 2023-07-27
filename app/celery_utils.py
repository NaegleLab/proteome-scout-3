def init_celery(celery, app):

    celery.conf.update(app.config)

    celery.conf.update(
        enable_utc = False,
        timezone = 'America/New_York'
    )
    # celery.conf.task_track_started = True
    # celery.conf.worker_send_task_events = True

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    
    return celery