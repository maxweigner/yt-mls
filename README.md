# yt-mls
YouTube Media Library Server aims to make downloading and updating media libraries easy.

# features
- Download of channels, playlists and videos in mp3 or mp4
- Download of processed files either individually or entire channels and playlists as a .zip
- Update of channels and playlists from the library
- Watching videos via an embed


# currently not supported
Having the same video in mp3 _and_ mp4 is not possible with how the download process and database work. This includes channels and playlists. The chosen type on initial download dictates what you have.


# media sources
Currently supported is YouTube but its possible expand since the download itself is handled by yt-dlp.


# deployment
To deploy this app, you need a production-ready WSGI server like Waitress. Do not use the Flask built-in development server.

## Deployment with waitress:
Clone the repo or download as zip and unpack.
Navigate into the created directory.

```
$ python -m venv .venv
$ . .venv/bin/activate
$ pip install -r requirements.txt
$ python server.py
```

Starting the server using `waitress.serve` is handled by server.py.
The default port is `5000` and can be changed by editing the `PORT` variable in the script.
