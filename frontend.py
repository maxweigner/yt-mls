from __future__ import unicode_literals

from flask import Blueprint, request, render_template, flash, send_from_directory, current_app
from flask_nav3 import Nav
from flask_nav3.elements import Navbar, View

from forms.download import DownloadForm
from backend import zip_folder, downloads_path, enqueue_download
from db_tools import query_db
from file_cache import *

frontend = Blueprint('frontend', __name__)

nav = Nav()
nav.register_element('frontend_top', Navbar(
    View('yt-dls', '.index'),
    View('downloader', '.downloader'),
    View('updater', '.updater'),
    View('library', '.library')
)
)


# there's basically nothing on index
# todo: a nice homepage or even a login could be nice
#  those that have a need for it and are able to make it secure, are invited to open a merge request
@frontend.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@frontend.route('/downloader', methods=['GET', 'POST'])
def downloader():
    # get form data
    form = DownloadForm()

    # get url out of form
    url = str(form.url.data)

    # check if valid link
    # this tool should technically work with other platforms but that is not tested
    # since KeyErrors are to be expected in backend.process_download(url), it's blocked here
    # you are invited to test and adjust the code for other platforms and open a merge request
    valid_link = True if 'youtube.com' in url or 'youtu.be' in url else False

    # if there has been a problem with the form (empty or error) or the link is not valid
    if not form.validate_on_submit() or not valid_link:
        valid_link = True if url == 'None' else False  # if url is empty, don't show error
        return render_template('downloader.html', form=form, ytLink=valid_link, titles=titles, urls=urls,
                               amount=len(titles))

    # kick off download process
    enqueue_download(url)

    # show download start confirmation
    flash('Download enqueued and will finish in background.')
    return render_template('feedback-simple.html', titles=titles, urls=urls, amount=len(titles))


# downloads a single file
@frontend.route('/download/<path:file_path>', methods=['GET'])
def download(file_path):
    # if the path does not end with a slash, a single file is requested
    if '.' in file_path:
        return send_from_directory(
            downloads_path(),
            file_path
        )

    # else a directory is requested
    else:
        # zip and send
        return send_from_directory(
            downloads_path(),
            file_path + zip_folder(file_path)
        )


@frontend.route('/update', methods=['GET', 'POST'])
def updater():
    downloads = query_db('SELECT name, url FROM updatelist INNER JOIN playlist ON updatelist.ROWID = playlist.ROWID')
    return render_template('updater.html', downloads=downloads)


@frontend.route('/update/<int:url_rowid>')
def update(url_rowid):
    url = query_db('SELECT url FROM updatelist WHERE ROWID = :url_rowid',
                   {'url_rowid': url_rowid})[0][0]

    # kick off download process
    enqueue_download(url)

    # show download start confirmation
    flash('Update enqueued and will finish in background.')
    return render_template('feedback-simple.html', titles=titles, urls=urls, amount=len(titles))


@frontend.route('/library', methods=['GET'])
def library():
    videos = query_db("SELECT name, ext, path FROM video")
    playlists = query_db("SELECT name, ROWID FROM playlist")
    return render_template('library.html', videos=videos, playlists=playlists, amount=len(playlists))


@frontend.route('/library-playlist', methods=['GET'])
def library_playlist():
    playlist = request.args.get('playlist', None)
    videos = query_db('SELECT video.name, video.ext, video.path FROM video LEFT JOIN collection ON video.id = '
                      'collection.video LEFT JOIN playlist ON collection.playlist=playlist.folder WHERE '
                      'playlist.ROWID = :playlist',
                      {'playlist': playlist})
    return render_template('collection.html', videos=videos)
