import pymysql
pymysql.version_info = (2, 2, 1, "final", 0)
pymysql.install_as_MySQLdb()

from .base import *
import os
from dotenv import load_dotenv

load_dotenv()

# rest of your settings...

from .base import *
import os
from dotenv import load_dotenv

load_dotenv()

DEBUG = False

ALLOWED_HOSTS = ['test.echulchul.art']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': 'localhost',
        'PORT': '3306',
    }
}

SECRET_KEY = os.getenv('SECRET_KEY')

STATIC_ROOT = '/home/echumggg/test.echulchul.art/static/'
MEDIA_ROOT = '/home/echumggg/test.echulchul.art/media/'
MEDIA_URL = '/media/'
STATIC_URL = '/static/'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/home/echumggg/echulchul.art/django_error.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}