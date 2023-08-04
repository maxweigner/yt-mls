from __future__ import unicode_literals


from flask import Blueprint, request, render_template, flash, send_from_directory, send_file

from forms.download import DownloadForm
from backend import zip_folder, zip_folder_not_in_directory, downloads_path, enqueue_download, internet_available
from db_tools import query_db
from file_cache import *

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
        return render_template('downloader.html', form=form, ytLink=valid_link, amount=len(urls))

    if not internet_available():
        flash('No internet connection available.', 'danger')
        return render_template('flash-message.html')

    # kick off download process
    enqueue_download(url, ext=ext)

    # show download start confirmation
    flash('Download enqueued and will finish in background.', 'primary')
    return render_template('flash-message.html')


# downloads a single file
@frontend.route('/download/<path:file_path>', methods=['GET'])
def download(file_path: str):
    # if the path does not end with a slash, a single file is requested
    if '.' in file_path:
        file_folder = ''.join([x if x not in file_path.split('/')[-1] else '' for x in file_path.split('/')])

        video = query_db('SELECT path, name, ext FROM video WHERE name = :name AND path = :path',
                         {'name': file_path.split('/')[-1].split('.')[0], 'path': file_folder + '\\' if file_folder else ''},
                         True)

        return send_from_directory(
            downloads_path() + video['path'],
            video['name'] + video['ext']
        )

    # else a directory is requested
    else:
        zip_path, zip_name = zip_folder(file_path)
        print(zip_path, zip_name)
        zip_folder_not_in_directory(zip_path + zip_name)

        # zip and send
        return send_from_directory(
            downloads_path() + zip_path,
            zip_name
        )


@frontend.route('/update/<int:url_rowid>', methods=['GET'])
def update(url_rowid):
    url = query_db('SELECT url FROM playlist WHERE ROWID = :url_rowid',
                   {'url_rowid': url_rowid})[0][0]

    # kick off download process
    enqueue_download(url, update=True)

    # show download start confirmation
    flash('Update enqueued and will finish in background.', 'primary')
    return render_template('flash-message.html', titles=titles, urls=urls, amount=len(urls))


@frontend.route('/library', methods=['GET'])
def library():
    videos = query_db("SELECT name, ext, path FROM video "
                      "LEFT JOIN collection ON video.id = collection.video WHERE collection.video IS NULL ")
    playlists = query_db("SELECT name, ROWID FROM playlist")
    if not playlists and not videos:
        flash('Library ist currently empty. Try downloading something!', 'primary')

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


@frontend.route('/player', methods=['GET'])
def player():
    return render_template('video-player.html')


@frontend.route('/serve', methods=['GET'])
def serve():
    file = request.args.get('file', None)
    if 'audio' in file:
        file = r'downloads\\CptCatman\\my vital organs all lift together.mp3'
        return send_file(
            file,
            'audio/mpeg',
            True
        )
    else:
        file = r'downloads\\Rick Astley - Never Gonna Give You Up (Official Music Video).webm'
        return send_file(
            file,
            'video/webm',
            True
        )
