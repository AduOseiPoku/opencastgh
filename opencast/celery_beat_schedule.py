from celery.schedules import crontab

# Add this to settings.py when you're ready to run Celery Beat
CELERY_BEAT_SCHEDULE = {
    'check-pending-transactions': {
        'task': 'voting.tasks.check_pending_transactions',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
}
