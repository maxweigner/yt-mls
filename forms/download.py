from flask_wtf import FlaskForm
from wtforms import URLField, SubmitField
from wtforms.validators import URL, DataRequired


class DownloadForm(FlaskForm):
    url = URLField('Video, Channel or Playlist', validators=[DataRequired(), URL()], render_kw={'placeholder': 'YouTube Link'})
    submit = SubmitField('Go')
