from waitress import serve
from app import create_app
import file_cache
import os

PORT = 5000
MAX_VIDEO_DOWNLOAD_LENGTH_MINUTES = 10

os.chdir(os.path.dirname(os.path.abspath(__file__)))
file_cache.max_video_length = MAX_VIDEO_DOWNLOAD_LENGTH_MINUTES * 60
serve(create_app(), port=PORT)
