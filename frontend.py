from flask import Blueprint, render_template, send_from_directory, request, current_app, g
from flask_nav3.elements import Navbar, View
import sqlite3
import os

import forms.download
from nav import nav
from forms.download import DownloadForm

frontend = Blueprint('frontend', __name__)

nav.register_element('frontend_top', Navbar(
    View('yt-dls', '.index'),
    View('downloader', '.downloader'),
    View('updater', '.updater'),
    View('library', '.library')
)
                     )


@frontend.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@frontend.route('/downloader', methods=['GET', 'POST'])
def downloader():
    form = DownloadForm()
    if form.validate_on_submit():
        # put here the interaction with youtube-dl
        # or forward to site that shows details of yt link
        url = form.url.data
        return f"Hello There {url}"

    return render_template('downloader.html', form=form)


@frontend.route('/download/<path:file>', methods=['GET'])
def download(file):
    return send_from_directory(
        os.path.join(current_app.root_path, 'downloads/'),
        file
    )


@frontend.route('/update', methods=['GET', 'POST'])
def updater():
    return render_template('updater.html')


@frontend.route('/library', methods=['GET'])
def library():
    videos = query_db("SELECT name FROM video")
    playlists = query_db("SELECT name FROM playlist")
    return render_template('library.html', videos=videos, playlists=playlists)


@frontend.route("/collection")
def collection():
    query = query_db("""
            SELECT video.name FROM video
            INNER JOIN collection ON collection.path = video.filename
            INNER JOIN playlist ON playlist.ROWID = collection.playlist
            WHERE video.name IS ?;
            """, ("",))
    return render_template('collection.html', query=query)


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect('files.sqlite')
    db.row_factory = sqlite3.Row
    return db


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    res = cur.fetchall()
    cur.close()
    return (res[0] if res else None) if one else res
