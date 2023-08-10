/*
    - unique youtube id / watch key identifies the song
    - id is nullable for ingest from filesystem
    - name is title of video
    - ext is the file extension / type
    - path is relative to 'project_root/downloads/'
 */
CREATE TABLE IF NOT EXISTS video (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    ext TEXT NOT NULL,
    path TEXT NOT NULL
);

/*
    - folder is relative to 'downloads/'
    - name is title of channel / playlist
    - if playlist name is new, all files
        go into 'downloads/name/'
    - if playlist name and therefore folder
        already exists, 'downloads/name/' dir
        gets subdirectories named after their
        respective ROWID
        example for folder:
            - 'playlist_name/'
            - 'playlist_name/playlist_ROWID/'
    - url is nullable for manual ingest
 */
CREATE TABLE IF NOT EXISTS playlist (
    folder TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT UNIQUE
);

/*
    - playlist equals folder
    - video equals id or rowid if from manual ingest
        - you better hope you dont have a video id with
            only numbers
    - simple n-m mapping
        (playlist contains multiple songs)
        (song can be in multiple playlists)
 */
CREATE TABLE IF NOT EXISTS collection (
    playlist TEXT NOT NULL,
    video TEXT NOT NULL
);

