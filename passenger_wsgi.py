import sys
import os
import traceback

try:
    venv_path = '/home/echumggg/virtualenv/echulchul.art/3.12/lib/python3.12/site-packages'
    sys.path.insert(0, venv_path)
    sys.path.insert(0, '/home/echumggg/echulchul.art')

    import pymysql
    pymysql.version_info = (2, 2, 1, "final", 0)
    pymysql.install_as_MySQLdb()

    from dotenv import load_dotenv
    load_dotenv('/home/echumggg/echulchul.art/.env')

    os.environ['DJANGO_SETTINGS_MODULE'] = 'echulchul.settings.production'

    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()

except Exception as e:
    error_msg = traceback.format_exc()
    with open('/home/echumggg/echulchul.art/wsgi_error.log', 'w') as f:
        f.write(error_msg)
    def application(environ, start_response):
        start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
        return [error_msg.encode()]