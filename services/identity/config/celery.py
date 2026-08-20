from ekomek_common.celery import create_celery_app

app = create_celery_app("identity")
