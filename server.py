from waitress import serve
from app import create_app
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

serve(create_app(), port=5000)
