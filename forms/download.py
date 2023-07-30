from flask_wtf import FlaskForm
from wtforms import URLField
from wtforms.validators import URL, DataRequired


class DownloadForm(FlaskForm):
    url = URLField('url', validators=[DataRequired(), URL()])
