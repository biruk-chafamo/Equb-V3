web: cd Equb && daphne -b 0.0.0.0 -p $PORT Equb.asgi:application
backgroundProcessor: python Equb/manage.py process_tasks -v2
release: python Equb/manage.py migrate