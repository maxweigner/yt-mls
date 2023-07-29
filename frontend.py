from flask import Blueprint, render_template, flash, redirect, url_for
from flask_bootstrap import __version__ as BOOTSTRAP_VERSION
from flask_nav3.elements import Navbar, View, Subgroup, Link, Text, Separator
from markupsafe import escape

from nav import nav

frontend = Blueprint('frontend', __name__)

nav.register_element('frontend_top', Navbar(
    View('yt-dls', '.index'),
    View('downloader', '.downloader'),
    View('updater', '.updater'),
    View('library', '.library')
)
                     )


@frontend.route('/')
def index():
    return render_template('index.html')


@frontend.route('/downloader')
def downloader():
    return render_template('downloader.html')


@frontend.route('/update')
def updater():
    return render_template('updater.html')


@frontend.route('/library')
def library():
    return render_template('library.html')
