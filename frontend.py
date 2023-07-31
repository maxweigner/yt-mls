from __future__ import unicode_literals

import os
import sqlite3
import yt_dlp as ydl

from flask import Blueprint, render_template, send_from_directory, current_app, g
from flask_nav3 import Nav
from flask_nav3.elements import Navbar, View

from forms.download import DownloadForm

frontend = Blueprint('frontend', __name__)

nav = Nav()
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

    url = str(form.url.data)

    # so error message does not get displayed when url is empty
    # validate_on_submit requires len(str) > 0 in DownloadForm
    ytLink = True
    titles = []
    urls = []

    if form.validate_on_submit():
        ytLink = True if 'youtube.com' in url else False
        if ytLink:
            query = ydl.YoutubeDL({'quiet': True}).extract_info(url=url, download=False)

            # if downloading playlist
            try:
                for video in query['entries']:
                    ydl.YoutubeDL({'quiet': True}).extract_info('https://www.youtube.com/watch?v=' + video['id'], download=False)
                    titles.append(video['title'])
                    urls.append('https://www.youtube.com/watch?v=' + video['id'])
                return render_template('downloader.html', form=form, ytLink=ytLink, titles=titles, urls=urls,
                                       amount=len(titles))
            except:
                pass

            # if downloading channel
            try:
                for tab in query['entries']:
                    for video in tab['entries']:
                        titles.append(video['title'])
                        urls.append('https://www.youtube.com/watch?v=' + video['id'])
                return render_template('downloader.html', form=form, ytLink=ytLink, titles=titles, urls=urls,
                                       amount=len(titles))
            except:
                pass

            # if downloading video
            try:
                titles.append(query['title'])
                urls.append('https://www.youtube.com/watch?v=' + query['id'])
                return render_template('downloader.html', form=form, ytLink=ytLink, titles=titles, urls=urls,
                                       amount=len(titles))
            except:
                pass

    return render_template('downloader.html', form=form, ytLink=ytLink, titles=titles, urls=urls, amount=len(titles))


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


def db_add_collection(info):
    return


def db_add_single(info):
    return


async def download_all(info):
    return


# todo: cache results from extract_info for /download and don't fetch again. update of existing downloads only over /update