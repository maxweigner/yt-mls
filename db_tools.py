from flask import g
import sqlite3
from file_cache import ids, titles


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
def db_add_via_download(ext, parent_rowid=None, parent=None):
    # if no parent was specified
    if parent is None:
        # insert video into db
        add_new_video(ids[0], titles[0], ext, '')

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
            add_new_video(ids[i], titles[i], ext, relative_path)
            add_collection_entry(relative_path, ids[i])

    return


def db_add_via_update(folder, ext):
    # insert all new files into db
    for i in range(len(titles)):
        add_new_video(ids[i], titles[i], ext, folder)
        add_collection_entry(folder, ids[i])

    return


def add_new_video(video_id, name, ext, path):
    query_db_threaded('INSERT INTO video(id, name, ext, path) VALUES (:id, :name, :ext, :path)',
                      {'id': video_id, 'name': name, 'ext': '.' + ext, 'path': path})
    return


def add_new_video_to_collection(parent, video_id):
    exists = query_db_threaded('SELECT * FROM collection WHERE playlist = :folder AND video = :id',
                               {'folder': parent + '\\', 'id': video_id})

    if not len(exists) > 0:
        add_collection_entry(parent + '\\', video_id)

    return


def add_collection_entry(folder, video_id):
    query_db_threaded('INSERT INTO collection(playlist, video) VALUES (:folder, :id)',
                      {'folder': folder, 'id': video_id})


def update_playlist_folder_by_rowid(folder, rowid):
    query_db_threaded('UPDATE playlist SET folder = :folder WHERE ROWID = :rowid',
                      {'folder': folder, 'rowid': rowid})
    return
