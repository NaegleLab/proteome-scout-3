from wtforms import Form, StringField, PasswordField, validators, SubmitField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, Length, Optional, Regexp


class SignupForm(Form):
    """User Signup Form."""

    username = StringField('Username', [DataRequired()])
    
    password = PasswordField('Password',
                             [DataRequired(),
                              Regexp('^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[!\"#$%&\'()*+,-./:;<=>?@\\[\]^_`{|}~]).{8,}', message="The new password must be at least 8 characters long and must contain one upper-case, one lower-case, one numeric and one special character")])
    confirm = PasswordField('Confirm Your Password',
                            [EqualTo('password', message='Passwords must match')] )
    name = StringField('Name',
                          [DataRequired()])
    email = StringField('Email',
                        [DataRequired(),
                         Email(message=('Please enter a valid email address.'))])
    institution = StringField('Institution',
                          [DataRequired()])
    submit = SubmitField('Register')


class LoginForm(Form):
    """User Login Form."""

    username = StringField('Username', [DataRequired()])
    password = PasswordField('Password', [DataRequired()])
    submit = SubmitField('Log In')