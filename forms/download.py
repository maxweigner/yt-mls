from flask_wtf import FlaskForm
from wtforms import URLField, SelectField, SubmitField
from wtforms.validators import URL, DataRequired, AnyOf


class DownloadForm(FlaskForm):
    url = URLField('Video, Channel or Playlist', validators=[DataRequired(), URL()], render_kw={'placeholder': 'URL'})
    ext = SelectField('Type', choices=[('mp3', 'Audio'), ('mp4', 'Video')], validators=[AnyOf(('mp3', 'mp4'))])
    submit = SubmitField('Go')
