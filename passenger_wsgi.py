import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/home/echumggg/echulchul_app/.env')

# Add project to path
sys.path.insert(0, '/home/echumggg/echulchul_app')

# Point to production settings
os.environ['DJANGO_SETTINGS_MODULE'] = 'echulchul.settings.production'

# Activate virtualenv
activate_env = '/home/echumggg/echulchul_app/venv/bin/activate_this.py'
with open(activate_env) as f:
    exec(f.read(), {'__file__': activate_env})

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()