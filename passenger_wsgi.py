import sys
import os

# Explicitly add venv packages to path FIRST before anything else
venv_path = '/home/echumggg/echulchul.art/venv/lib64/python3.12/site-packages'
venv_path2 = '/home/echumggg/echulchul.art/venv/lib/python3.12/site-packages'
sys.path.insert(0, venv_path)
sys.path.insert(0, venv_path2)
sys.path.insert(0, '/home/echumggg/echulchul.art')

import pymysql
pymysql.version_info = (2, 2, 1, "final", 0)
pymysql.install_as_MySQLdb()

from dotenv import load_dotenv
load_dotenv('/home/echumggg/echulchul.art/.env')

os.environ['DJANGO_SETTINGS_MODULE'] = 'echulchul.settings.production'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()