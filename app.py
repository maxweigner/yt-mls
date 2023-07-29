from flask import Flask
from flask_bootstrap import Bootstrap

from frontend import frontend
from nav import nav


def create_app():
    app = Flask(__name__)
    Bootstrap(app)

    app.config['BOOTSTRAP_SERVE_LOCAL'] = True
    app.register_blueprint(frontend)
    nav.init_app(app)

    return app
