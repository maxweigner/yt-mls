from flask import Flask, current_app, g
from flask_wtf.csrf import CSRFProtect

from frontend import frontend
from backend import get_db
from os import urandom


def init_db():
    with current_app.app_context():
        db = get_db()
        with current_app.open_resource('schema.sql', mode='r') as schema:
            db.cursor().executescript(schema.read())


def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = urandom(32)
    CSRFProtect(app)

    app.register_blueprint(frontend)
    app.app_context().push()

    init_db()

    return app


@frontend.teardown_request
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()
