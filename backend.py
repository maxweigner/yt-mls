import threading
import yt_dlp as ydl
import os
import zipfile

from datetime import datetime
from urllib.request import urlopen
from urllib.error import URLError
from base64 import b64encode
from threading import Thread
from shutil import rmtree

from db_tools import (
    add_new_video_to_collection,
    query_db_threaded,
    db_add_via_update,
    db_add_via_download,
    update_playlist_folder_by_rowid,
    remove_video,
    remove_playlist
)
from file_cache import *
from utils import downloads_path, dissect_file_name


# adds thread to queue and starts it
def enqueue_download(url, update=False, ext='mp3'):
    # download and processing is happening in background / another thread
    t = Thread(target=process_general, args=(url, ext, update))
    thread_queue.append(t)
    t.start()
    return


def process_general(url, ext, update=False):
    # get current time
    current_time = datetime.now().time()

    # parse hour and minute
    hour = str(current_time.hour)
    hour = hour if len(hour) > 1 else '0' + hour
    minute = str(current_time.minute)
    minute = minute if len(minute) > 1 else '0' + minute

    # add url and time to list of queued downloads
    queued_downloads.append([url, hour + ':' + minute])

    # wait for previous thread to finish if not first / only in list
    current_thread = threading.current_thread()
    if len(thread_queue) > 0 and thread_queue[0] is not current_thread:
        threading.Thread.join(thread_queue[thread_queue.index(current_thread) - 1])

    # clear file_cache
    ids.clear()
    titles.clear()
    urls.clear()

    # get basic info for given url
    query = ydl.YoutubeDL({'quiet': True, 'ignoreerrors': True}).extract_info(url=url, download=False)
    parent = query['title']

    if update:
        process_update(parent, query, current_thread)
    else:
        process_download(url, ext, parent, query, current_thread)

    try:
        queued_downloads.pop(0)
    except IndexError:
        print('*** IndexError: download could not be removed from list of running downloads. ***')

    return


# this is the 'controller' for the download process
def process_download(url, ext, parent, query, current_thread):
    # one of the three cases does not throw an exception
    # and therefore gets to download and return
    # kinda hacky but whatever

    # if downloading playlist
    try:
        # this throws KeyError when downloading single file
        for video in query['entries']:
            if video is None:
                continue

            video['title'] = sanitize_filename(video['title'])

            if check_already_exists(video['id']):
                add_new_video_to_collection(parent, video['id'])
                continue

            # this throws DownloadError when not downloading playlist
            ydl.YoutubeDL({'quiet': True}).extract_info('https://www.youtube.com/watch?v=' + video['id'],
                                                        download=False)

            # replace url with name of playlist
            queued_downloads[0][0] = sanitize_filename(parent)

            if max_video_length and video['duration'] > max_video_length:
                continue

            # add new entry to file_cache
            ids.append(video['id'])
            titles.append(video['title'])
            urls.append('https://www.youtube.com/watch?v=' + video['id'])

        # start download
        download_all(url, ext, parent)
        thread_queue.remove(current_thread)
        return

    # when downloading: channel: DownloadError, single file: KeyError
    except (ydl.DownloadError, KeyError):
        pass

    # if downloading channel
    try:
        # for every tab (videos/shorts)
        for tab in query['entries']:
            # for every video in their respective tabs
            for video in tab['entries']:
                if video is None:
                    continue

                video['title'] = sanitize_filename(video['title'])

                if check_already_exists(video['id']):
                    add_new_video_to_collection(parent, video['id'])
                    continue

                # replace url with name of channel
                queued_downloads[0][0] = sanitize_filename(parent)

                if max_video_length and video['duration'] > max_video_length:
                    continue

                # there have been cases of duplicate urls or some with '/watch?v=@channel_name'
                # but no consistency has been observed
                # still works though so will not be checked for now
                ids.append(video['id'])
                titles.append(video['title'])
                urls.append('https://www.youtube.com/watch?v=' + video['id'])

        # start download
        download_all(url, ext, parent)
        thread_queue.remove(current_thread)
        return

    # when downloading single file: KeyError
    except KeyError:
        pass

    # if downloading video
    try:
        # when downloading single files that already exist, there's no need for adjustments in db
        if not check_already_exists(query['id']):
            ids.append(query['id'])
            query['title'] = sanitize_filename(query['title'])
            titles.append(query['title'])
            urls.append('https://www.youtube.com/watch?v=' + query['id'])
        else:
            return

        # replace url with name of video
        queued_downloads[0][0] = query['title']

        # start download
        download_all(url, ext=ext)

    # this is broad on purpose; there has been no exception thrown here _yet_
    except Exception as e:
        print('*** ' + str(e) + ' ***')

    thread_queue.remove(current_thread)
    return


# this is the 'controller' for the update process
def process_update(parent, query, current_thread):
    # replace url with name of playlist
    queued_downloads[0][0] = sanitize_filename(parent)

    # if updating playlist
    try:
        # this throws KeyError when downloading single file
        for video in query['entries']:
            if video is None:
                continue

            video['title'] = video['title'].replace('/', '⧸').replace('|', '｜')

            if check_already_exists(video['id']):
                add_new_video_to_collection(parent, video['id'])
                continue

            # this throws DownloadError when not downloading playlist
            ydl.YoutubeDL({'quiet': True}).extract_info('https://www.youtube.com/watch?v=' + video['id'],
                                                        download=False)

            if max_video_length and video['duration'] > max_video_length:
                continue

            # add new entry to file_cache
            ids.append(video['id'])
            titles.append(video['title'])
            urls.append('https://www.youtube.com/watch?v=' + video['id'])

        # start update
        update_all()
        thread_queue.remove(current_thread)
        return

    # when downloading: channel: DownloadError, single file: KeyError
    except (ydl.DownloadError, KeyError):
        pass

    # if downloading channel
    try:
        # for every tab (videos/shorts)
        for tab in query['entries']:
            # for every video in their respective tabs
            for video in tab['entries']:
                if video is None:
                    continue

                video['title'] = video['title'].replace('/', '⧸').replace('|', '｜')

                if check_already_exists(video['id']):
                    add_new_video_to_collection(parent, video['id'])
                    continue

                if max_video_length and video['duration'] > max_video_length:
                    continue

                # there have been cases of duplicate urls or some with '/watch?v=@channel_name'
                # but no consistency has been observed
                # still works though so will not be checked for now
                ids.append(video['id'])
                titles.append(video['title'])
                urls.append('https://www.youtube.com/watch?v=' + video['id'])

        # start download
        update_all()
        thread_queue.remove(current_thread)
        return
    except KeyError:
        pass

    thread_queue.remove(current_thread)
    return


# checks whether a video is already in db
def check_already_exists(video_id) -> bool:
    res = query_db_threaded('SELECT name FROM video WHERE id = :id',
                            {'id': video_id})
    if len(res) > 0:
        return True
    return False


def download_all(url, ext, parent=None):
    # if no new files to download, there's nothing to do here
    if not len(urls) > 0: return

    # new parent rowid
    rowid_new = None

    # if a parent was specified
    if parent is not None:
        # insert new playlist into db and get the rowid of the new entry
        rowid_new = query_db_threaded('INSERT INTO playlist(name, url) VALUES (:name, :url) RETURNING ROWID',
                                      {'name': parent, 'url': url},
                                      True)[0]

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
                                                 {'playlist': parent},
                                                 True)[0]

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
            update_playlist_folder_by_rowid(relativePath, rowid_new)

            # set path for new downloads
            location = downloads_path() + relativePath

        # if that subdirectory does not already exist
        else:
            # set the relative path of playlist in recently added entry
            update_playlist_folder_by_rowid(relativePath, rowid_new)

            # db_add needs to be passed none so the correct folder can be set in collection
            rowid_new = None

            # set path for new downloads
            location = downloads_path() + relativePath

    # if no parent was specified
    else:
        location = downloads_path()

    # start actual file download
    yt_download(location, ext)

    # add downloaded files to db
    db_add_via_download(ext, rowid_new, parent)

    return


def update_all():
    ext, folder = query_db_threaded('SELECT video.ext, playlist.folder FROM video '
                                    'INNER JOIN collection ON video.id=collection.video '
                                    'INNER JOIN playlist ON collection.playlist=playlist.folder',
                                    {},
                                    True)

    yt_download(downloads_path() + folder, ext[1:])
    db_add_via_update(folder, ext[1:])
    return


# actually downloads files
def yt_download(location, ext='mp3'):
    # base download options for audio
    opts = {
        'quiet': True,
        'ignoreerrors': True,
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
        opts['format'] = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]'
        opts['merge_output_format'] = 'mp4'
        opts.pop('postprocessors')

    # try to download all new files
    ydl.YoutubeDL(opts).download(urls)

    return


# updates zip in or creates new zip of given directory
def zip_folder(full_rel_path) -> tuple[str, str]:
    # get playlist name
    parent = full_rel_path.split('/')
    for folder in parent:
        if folder != '' and not folder.isdigit():
            parent = folder
            break

    # get filename of existing zip else empty string
    existing_zip_name = directory_contains_zip(full_rel_path)

    # get or generate filename
    if existing_zip_name:
        filename = existing_zip_name
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

    # add remaining files to zip
    with zipfile.ZipFile(downloads_path() + full_rel_path + filename, 'a') as existing_zip:
        file_list = existing_zip.namelist()
        file_list = [e[len(parent)+1:] for e in file_list]

        for entry in os.scandir(downloads_path() + full_rel_path):
            if entry.is_file() and not entry.name.endswith('.zip') and entry.name not in file_list:
                # Add the file to the zip, preserving the directory structure
                existing_zip.write(entry.path, arcname=parent + '/' + entry.name)

    return full_rel_path, filename


# adds all files that are in the playlist but not in its folder to the zip
def zip_folder_not_in_directory(zip_full_rel_path):
    video_not_in_directory = query_db_threaded('SELECT path, name, ext FROM video '
                                               'INNER JOIN collection ON video.id = collection.video '
                                               'WHERE NOT path = playlist')

    # get full path to downloads directory
    downloads_folder = downloads_path()

    # add remaining files to zip
    with zipfile.ZipFile(downloads_folder + zip_full_rel_path, 'a') as existing_zip:
        file_list_zip = existing_zip.namelist()
        file_list_files = [e.split('/')[-1] for e in file_list_zip]
        file_list_folder = file_list_zip[0].split('/')[0]

        for video in video_not_in_directory:
            file_name = video[1] + video[2]
            if file_name not in file_list_files:
                existing_zip.write(downloads_folder + video[0] + file_name, arcname=file_list_folder + '/' + file_name)

    return


# returns name of first zip found or empty string
def directory_contains_zip(full_rel_path):
    for file in os.scandir(downloads_path() + full_rel_path):
        if file.name.endswith('.zip'):
            return file.name
    return ''


# checks if yt or any given target can be reached
def internet_available(target='http://www.youtube.com'):
    try:
        urlopen(target)
        return True
    except URLError:
        return False


# does what it says; does not need thread of its own since it's reasonably fast
def delete_file_or_playlist(file_name):
    # deleting single download is simple enough
    if '.' in file_name:
        remove_video(file_name)
        os.remove(downloads_path() + file_name)
        return

    # get folder from file_name
    folder, _, _ = dissect_file_name(file_name)

    # remove playlist from db and get videos that are also in other playlists
    # todo: this needs to be tested at some point
    videos_to_move = remove_playlist(folder)

    # move all videos rescued from being deleted
    if videos_to_move:
        for video in videos_to_move:
            os.rename(
                downloads_path() + video[0] + video[1] + video[2],
                downloads_path() + video[1] + video[2]
            )

    # delete the folder in which the playlist was stored
    rmtree(downloads_path() + folder)
    return


# checks if file is somewhere in downloads directory and returns true if so
def check_file_path(path):
    downloads = downloads_path()
    return downloads in os.path.abspath(downloads + path)


# sanitizes file names for windows fs
# replaces the chars with those used by yt-dlp as a substitution
def sanitize_filename(file_name: str):
    # '<' and '>' are not allowed on yt
    return (file_name
            .replace('\\', '⧹')
            .replace('/', '⧸')
            .replace('|', '｜')
            .replace(':', '：')
            .replace('*', '＊')
            .replace('?', '？')
            .replace('"', '＂'))
