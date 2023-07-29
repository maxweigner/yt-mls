from flask import Flask, current_app, g
from flask_bootstrap import Bootstrap

from frontend import frontend, get_db
from nav import nav


def init_db():
    with current_app.app_context():
        db = get_db()
        with current_app.open_resource('schema.sql', mode='r') as schema:
            db.cursor().executescript(schema.read())


def create_app():
    app = Flask(__name__)
    Bootstrap(app)

    app.config['BOOTSTRAP_SERVE_LOCAL'] = True
    app.register_blueprint(frontend)
    app.app_context().push()
    nav.init_app(app)

    init_db()

    return app


@frontend.teardown_request
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()
