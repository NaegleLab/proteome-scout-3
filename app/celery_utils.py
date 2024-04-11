from celery.schedules import crontab

def init_celery(celery, app):
    celery.conf.update(app.config)

    celery.conf.update(
        enable_utc = False,
        timezone = 'America/New_York', 
        broker_pool_limit = None, 
    )

    celery.conf.beat_schedule = {"run-me-on_wednesday": {
        "task": "scripts.export.test_task.test",
        "schedule": crontab(minute=29, hour=0, day_of_week='wednesday'),
        "args": ("hello",)
        }
    }
    
    # celery.conf.beat_schedule = {"run-me-every-ten-seconds": {
    #     "task": "scripts.export.test_task.test",
    #     "schedule": 10.0,
    #     "args": ("hello",)
    #     }
    # }

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery