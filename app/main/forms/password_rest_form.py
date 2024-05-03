from wtforms import StringField, TextAreaField, BooleanField, SubmitField, validators
from wtforms.validators import InputRequired
from flask_wtf import FlaskForm


class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[validators.DataRequired(), validators.Email()])
    submit = SubmitField('Request Password Reset')