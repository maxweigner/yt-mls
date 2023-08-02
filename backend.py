import threading

from flask import g
import yt_dlp as ydl
from yt_dlp import DownloadError
import os
import zipfile
import sqlite3
from base64 import b64encode

from file_cache import *


# this is the 'controller' for the download process
def process_download(url):
    # wait for previous thread if not first in list
    current_thread = threading.current_thread()
    if len(thread_queue) > 0 and thread_queue[0] is not current_thread:
        threading.Thread.join(thread_queue[thread_queue.index(current_thread) - 1])

    # clear file_cache
    ids.clear()
    titles.clear()
    urls.clear()

    # get basic info for given url
    query = ydl.YoutubeDL({'quiet': True}).extract_info(url=url, download=False)
    parent = query['title']

    # one of the three cases does not throw an exception
    # and therefore gets to download and return
    # kinda hacky but whatever

    # if downloading playlist
    try:
        # this throws KeyError when downloading single file
        for video in query['entries']:
            if check_already_exists(video['id']):  # todo: this shit aint tested
                query_db_threaded('INSERT INTO collection(playlist, video) VALUES (:folder, :id)',
                                  {'folder': parent + '\\', 'id': video['id']})
                continue

            # this throws DownloadError when not downloading playlist
            ydl.YoutubeDL({'quiet': True}).extract_info('https://www.youtube.com/watch?v=' + video['id'],
                                                        download=False)
            # add new entry to file_cache
            ids.append(video['id'])
            titles.append(video['title'])
            urls.append('https://www.youtube.com/watch?v=' + video['id'])

        # start download
        download_all(parent)
        return

    # when downloading: channel: DownloadError, single file: KeyError
    except (DownloadError, KeyError):
        pass

    # if downloading channel
    try:
        # for every tab (videos/shorts)
        for tab in query['entries']:
            # for every video in their respective tabs
            for video in tab['entries']:
                if check_already_exists(video['id']):
                    query_db_threaded('INSERT INTO collection(playlist, video) VALUES (:folder, :id)',
                                      {'folder': parent + '\\', 'id': video['id']})
                    continue

                # todo: there have been cases of duplicate urls or some with '/watch?v=@channel_name'
                #  but no consistency has been observed
                #  still works though so will not be checked for now
                ids.append(video['id'])
                titles.append(video['title'])
                urls.append('https://www.youtube.com/watch?v=' + video['id'])

        # start download
        download_all(parent)
        return

    # when downloading single file: KeyError
    except KeyError:
        pass

    # if downloading video
    try:
        # when downloading single files that already exist, there's no need for adjustments in db
        if not check_already_exists(query['id']):
            ids.append(query['id'])
            titles.append(query['title'])
            urls.append('https://www.youtube.com/watch?v=' + query['id'])

        # start download
        download_all()
        return

    # this is broad on purpose; there has been no exception thrown here _yet_
    except Exception as e:
        print('*** ' + str(e) + ' ***')

    # todo: a site with (not) finished downloads (url/datetime) would be nice so you know when it's done
    #  downloading large playlists does take quite a while after all
    #  adding that entry to the site would be done -here- i guess

    thread_queue.remove(current_thread)
    return


# checks whether a video is already in db
def check_already_exists(video_id) -> bool:
    res = query_db_threaded('SELECT name FROM video WHERE id = :id', {'id': video_id})
    if len(res) > 0:
        return True
    return False


# fetches db from app context
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect('files.sqlite')
        db.row_factory = sqlite3.Row
    return db


# used when accessing db from app context; keeps connection alive since it's used more frequently
def query_db(query, args=(), one=False):
    db = get_db()
    cur = db.execute(query, args)
    res = cur.fetchall()
    db.commit()
    cur.close()
    return (res[0] if res else None) if one else res


# used when accessing db from thread, since app context is thread local; does not keep connection alive
def query_db_threaded(query, args=(), one=False):
    db = sqlite3.connect('files.sqlite')
    cur = db.execute(query, args)
    res = cur.fetchall()
    db.commit()
    cur.close()
    db.close()
    return (res[0] if res else None) if one else res


# add entries do db
def db_add(ext, parent_rowid=None, parent=None):
    # if no parent was specified
    if parent is None:
        # insert video into db
        query_db_threaded('INSERT INTO video(id, name, ext, path) VALUES (:id, :name, :ext, :path)',
                          {'id': ids[0], 'name': titles[0], 'ext': '.' + ext, 'path': '\\'})

    # if a parent was specified
    else:
        # set relative path
        relative_path = parent + '\\'

        # if a rowid was specified
        if parent_rowid is not None:
            # adjust the relative path
            relative_path += str(parent_rowid) + '\\'

        # insert all new files into db
        for i in range(len(titles)):
            query_db_threaded('INSERT INTO video(id, name, ext, path) VALUES (:id, :name, :ext, :path)',
                              {'id': ids[i], 'name': titles[i], 'ext': '.' + ext, 'path': relative_path})
            query_db_threaded('INSERT INTO collection(playlist, video) VALUES (:folder, :id)',
                              {'folder': relative_path, 'id': ids[i]})

    return


def download_all(parent=None, ext='mp3'):
    # if no new files to download, there's nothing to do here
    if not len(urls) > 0: return

    # new parent rowid
    rowid_new = None

    # if a parent was specified
    if parent is not None:
        # insert new playlist into db and get the rowid of the new entry
        rowid_new = query_db_threaded('INSERT INTO playlist(name) VALUES (:name) RETURNING ROWID',
                                      {'name': parent})[0][0]

        # set the base relative path for playlists
        relativePath = parent + '\\'

        # does that subdirectory already exist?
        if os.path.exists(f'downloads\\{parent}'):
            subdirs = []
            for file in os.scandir(f'downloads\\{parent}'):
                if file.is_dir():
                    subdirs.append(file)

            # was that subdirectory not split into subdirectories already? (duplicate playlist names)
            if not len(subdirs) > 0:
                # get rowid of current playlist in 'downloads/parent/' directory
                parent_rowid = query_db_threaded('SELECT ROWID FROM playlist WHERE name = :playlist',
                                                 {'playlist': parent})[0][0]

                # update previous parents directory
                query_db_threaded('UPDATE playlist SET folder = :folder WHERE ROWID = :rowid',
                                  {'folder': relativePath + str(parent_rowid) + '\\', 'rowid': parent_rowid})

                # update the folder entry in collection
                query_db_threaded('UPDATE collection SET playlist = :folder WHERE playlist = :folder_old',
                                  {'folder': relativePath + str(parent_rowid) + '\\', 'folder_old': relativePath})

                # move all files into subdirectory 'downloads/parent/rowid'
                srcpath = downloads_path() + parent + '\\'
                dstpath = srcpath + str(parent_rowid) + '\\'
                for f in os.scandir(srcpath):
                    os.renames(srcpath + f.name, dstpath + f.name)

                # adjust path in db table video
                query_db_threaded('UPDATE video SET path = :new_path WHERE path = :old_path',
                                  {'new_path': relativePath + str(parent_rowid) + '\\', 'old_path': relativePath})

                # append relative path
                relativePath += str(rowid_new) + '\\'

            # set the relative path of playlist in recently added entry
            query_db_threaded('UPDATE playlist SET folder = :folder WHERE ROWID = :rowid',
                              {'folder': relativePath, 'rowid': rowid_new})

            # set path for new downloads
            location = downloads_path() + relativePath

        # if that subdirectory does not already exist
        else:
            # set the relative path of playlist in recently added entry
            query_db_threaded('UPDATE playlist SET folder = :folder WHERE ROWID = :rowid',
                              {'folder': relativePath, 'rowid': rowid_new})

            # db_add needs to be passed none so the correct folder can be set in collection
            rowid_new = None

            # set path for new downloads
            location = downloads_path() + relativePath

    # if no parent was specified
    else:
        location = downloads_path()

    # base download options for audio
    opts = {
        'quiet': False,
        'windowsfilenames': True,
        'outtmpl': location + '%(title)s.%(ext)s',
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': 192
        }]
    }

    # if videos are wanted, adjust the options
    if ext == 'mp4':
        opts.pop('format')
        opts.pop('postprocessors')

    # try to download all new files
    try:
        ydl.YoutubeDL(opts).download(urls)
    except DownloadError:
        pass

    # add downloaded files to db
    db_add(ext, rowid_new, parent)

    return


# a way to get the 'parent_root/downloads' directory; alternative for nonexistent global immutable
# since app context does not exist where this is called, using app.config will not work
def downloads_path() -> str:
    return os.path.dirname(os.path.abspath(__file__)) + '\\downloads\\'


# updates zip in or creates new zip of given directory
def zip_folder(full_rel_path):
    # get playlist name
    parent = full_rel_path.split('/')
    for folder in parent:
        if folder != '' and not folder.isdigit():
            parent = folder
            break

    # get filename of existing zip else empty string
    existing_zip = directory_contains_zip(full_rel_path)

    # get or generate filename
    if existing_zip:
        filename = existing_zip
    else:
        # generate filename without slashes as that might be a problem but that was not tested
        filename = (b64encode(os.urandom(4)).decode('utf-8')
                    .replace('/', 'x')
                    .replace('\\', 'y')
                    .replace('=', 'z')
                    .replace('+', 'a')
                    ) + '.zip'

        # create archive
        zipfile.ZipFile(downloads_path() + full_rel_path + filename, 'w')

    # Open the existing zip file in append mode
    with zipfile.ZipFile(downloads_path() + full_rel_path + filename, 'a') as existing_zip:
        file_list = existing_zip.namelist()
        file_list = [e[len(parent)+len(downloads_path())+1:] for e in file_list]

        for entry in os.scandir(downloads_path() + full_rel_path):
            if entry.is_file() and not entry.name.endswith('.zip') and entry.name not in file_list:
                # Add the file to the zip, preserving the directory structure
                existing_zip.write(entry.path, arcname=parent + '\\' + entry.name)

    return filename


def directory_contains_zip(full_rel_path):
    for file in os.scandir(downloads_path() + full_rel_path):
        if file.name.endswith('.zip'):
            return file.name
    return ''
