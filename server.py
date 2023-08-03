from waitress import serve
from app import create_app
import os

PORT = 5000

os.chdir(os.path.dirname(os.path.abspath(__file__)))

serve(create_app(), port=PORT)
