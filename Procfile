web: cd Equb && gunicorn Equb.wsgi:application 
backgroundProcessor: python Equb/manage.py process_tasks -v2
release: python Equb/manage.py migrate