import os
import sys
from dotenv import load_dotenv

load_dotenv('/home/echumggg/echulchul.art/.env')

sys.path.insert(0, '/home/echumggg/echulchul.art')

os.environ['DJANGO_SETTINGS_MODULE'] = 'echulchul.settings.production'

activate_env = '/home/echumggg/echulchul.art/venv/bin/activate_this.py'
with open(activate_env) as f:
    exec(f.read(), {'__file__': activate_env})

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()