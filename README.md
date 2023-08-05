## yt-mls
YouTube Media Library Server aims to make downloading and updating media libraries easy.


## features
- Download of channels, playlists and videos in mp3 or mp4
- Download of processed files either individually or entire channels and playlists as a .zip
- Update of channels and playlists from the library
- Watching videos via an embed
- Listening to song via an embed

## media sources
Currently supported is YouTube but its possible to expand since the download itself is handled by yt-dlp.


## deployment
To deploy this app, you need a production-ready WSGI server like Waitress. Do not use the Flask built-in development server.


### waitress in truenas jail
The following works in a 13.2 base jail:
```
$ git clone https://github.com/maxweigner/yt-mls.git
$ cd yt-mls
$ pkg install python39 py39-pip py39-sqlite3 ffmpeg
$ pip install -r requirements.txt
$ pip install supervisord
$ python -m venv venv
$ source venv/bin/activate.csh
$ pip install -r requirements.txt
$ touch supervisord.conf
```
Put the following into `supervisord.conf`
```
[supervisord]

[program:ytmls]
command=/usr/local/bin/python /root/yt-mls/server.py ;
directory=/root/yt-mls ;
autostart=true ;
autorestart=true ;
```
Run `crontab -e` and add the following line
```
@reboot /usr/local/bin/supervisord -c /root/yt-mls/supervisord.conf
```
Restart the jail and you're done.


### configuration

Starting the server using `waitress.serve` is handled by server.py.
The default port is `5000` and can be changed by editing the `PORT` variable in the script. 

If you want to limit the duration of videos you want to download e.g. if you want to download only single titles from a playlist with mixes, set `MAX_VIDEO_DOWNLOAD_LENGTH_MINUTES` to the desired amount. Default is `10` minutes.


## currently not supported
Having the same video in mp3 _and_ mp4 is not possible with how the download process and database work. This includes channels and playlists. The chosen type on initial download dictates what you have.
