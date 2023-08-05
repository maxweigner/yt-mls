from __future__ import unicode_literals

import os.path

from flask import (
    Blueprint,
    request,
    render_template,
    redirect,
    flash,
    send_from_directory,
    send_file
)
from backend import (
    zip_folder,
    zip_folder_not_in_directory,
    enqueue_download,
    internet_available,
    delete_file_or_playlist,
    check_file_path
)
from forms.download import DownloadForm
from db_tools import query_db
from file_cache import *
from utils import downloads_path, dissect_file_name

frontend = Blueprint('frontend', __name__)


# index has a list of running downloads
@frontend.route('/', methods=['GET'])
def index():
    if not queued_downloads:
        flash('Currently, no downloads are running.', 'primary')
    return render_template('index.html', running_downloads=queued_downloads, titles=titles, urls=urls, amount=len(urls))


@frontend.route('/downloader', methods=['GET', 'POST'])
def downloader():
    # get form data
    form = DownloadForm()

    # get url out of form
    url = str(form.url.data)
    ext = str(form.ext.data)

    # check if high likelihood of being a valid link
    # this tool should technically work with other platforms but that is not tested
    # since KeyErrors are to be expected in backend.process_download(url), it's blocked here
    # you are invited to test and adjust the code for other platforms
    valid_link = True if 'youtube.com' in url or 'youtu.be' in url else False

    # if there has been a problem with the form (empty or error) or the link is not valid
    if not form.validate_on_submit() or not valid_link:
        valid_link = True if url == 'None' else False  # if url is empty, don't show error
        return render_template('downloader.html', form=form, amount=len(urls))

    if not internet_available():
        flash('No internet connection available.', 'danger')
        return render_template('flash-message.html')

    # kick off download process
    enqueue_download(url, ext=ext)

    # show download start confirmation
    flash('Download enqueued and will finish in background.', 'primary')
    return redirect('/downloader')


@frontend.route('/library', methods=['GET'])
def library():
    videos = query_db("SELECT name, ext, path FROM video "
                      "LEFT JOIN collection ON video.id = collection.video WHERE collection.video IS NULL ")
    playlists = query_db("SELECT name, ROWID FROM playlist")
    if not playlists and not videos:
        flash('Library ist currently empty. Try downloading something!', 'primary')

    # todo: searching your library for a song would be nice

    return render_template('library.html', videos=videos, playlists=playlists, amount=len(playlists))


@frontend.route('/library-playlist', methods=['GET'])
def library_playlist():
    playlist = request.args.get('playlist', None)
    videos = query_db('SELECT video.name, video.ext, video.path FROM video '
                      'LEFT JOIN collection ON video.id = collection.video '
                      'LEFT JOIN playlist ON collection.playlist=playlist.folder '
                      'WHERE playlist.ROWID = :playlist',
                      {'playlist': playlist})

    # get playlist path since could be empty in some entries
    folder = ''
    for video in videos:
        if len(video['path']) > 0:
            folder = video['path']
            break

    return render_template('collection.html', videos=videos, folder=folder)


# sends file or playlist to client
@frontend.route('/download', methods=['GET'])
def download():
    file_path = request.args.get('file')
    # if the path does not end with a slash, a single file is requested
    if '.' in file_path:
        path, name, ext = dissect_file_name(file_path)

        # this is flaky for whatever reason; might be because of special chars?
        return send_from_directory(
            'downloads/' + path,
            name + ext
        )

    # else a directory is requested
    else:
        zip_path, zip_name = zip_folder(file_path)
        zip_folder_not_in_directory(zip_path + zip_name)

        # zip and send
        return send_from_directory(
            downloads_path() + zip_path,
            zip_name
        )


@frontend.route('/delete', methods=['GET'])
def delete():
    file_name = request.args.get('file')
    delete_file_or_playlist(file_name)

    if '.' in file_name:
        flash('File has been deleted.', 'primary')
    else:
        flash('Playlist has been deleted.', 'primary')

    return redirect('/library')


@frontend.route('/update', methods=['GET'])
def update():
    url_rowid = request.args.get('list')
    url = query_db('SELECT url FROM playlist WHERE ROWID = :url_rowid',
                   {'url_rowid': url_rowid},
                   True)[0]

    # kick off download process
    enqueue_download(url, update=True)

    # show download start confirmation
    flash('Update enqueued and will finish in background.', 'primary')
    return redirect(request.args.get('from'))


# player as well as serve are placeholders for now
# todo: add functionality to library
@frontend.route('/player', methods=['GET'])
def player():
    return render_template('player.html', file=request.args.get('file'))


@frontend.route('/serve', methods=['GET'])
def serve():
    file = request.args.get('file')
    if not check_file_path(file):
        flash('Video not found', 'danger')
        return render_template('flash-message.html')

    if 'mp3' in file:
        return send_file(
            downloads_path() + file,
            'audio/mpeg',
            True
        )
    elif 'mp4' in file:
        return send_file(
            downloads_path() + file,
            'video/mp4',
            True
        )
