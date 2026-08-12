web: daphne -b 0.0.0.0 -p $PORT config.asgi:application
backgroundProcessor: python manage.py process_tasks -v2
release: python manage.py migrate
