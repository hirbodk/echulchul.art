import sys
import os

# Log errors to a file we can read
import traceback

try:
    import pymysql
    pymysql.version_info = (2, 2, 1, "final", 0)
    pymysql.install_as_MySQLdb()

    from dotenv import load_dotenv
    load_dotenv('/home/echumggg/echulchul.art/.env')

    sys.path.insert(0, '/home/echumggg/echulchul.art')
    os.environ['DJANGO_SETTINGS_MODULE'] = 'echulchul.settings.production'

    activate_env = '/home/echumggg/echulchul.art/venv/bin/activate_this.py'
    with open(activate_env) as f:
        exec(f.read(), {'__file__': activate_env})

    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()

except Exception as e:
    error_msg = traceback.format_exc()
    # Write error to a readable file
    with open('/home/echumggg/echulchul.art/wsgi_error.log', 'w') as f:
        f.write(error_msg)

    # Also show it in the browser temporarily
    def application(environ, start_response):
        start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
        return [error_msg.encode()]