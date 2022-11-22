from flask import render_template, redirect, flash, url_for, request
from flask_login import login_required, logout_user, current_user, login_user

from app.database.user import User, load_user_by_username, load_user_by_email
from app.auth.forms import LoginForm, SignupForm
from app.auth import bp
from app import db

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('proteomescout/landing'))
    login_form = LoginForm(request.form)

    if request.method == 'POST':
        if login_form.validate():
            # Get Form Fields
            username = request.form.get('username')
            password = request.form.get('password')
            # Validate Login Attempt
            user = load_user_by_username(username)
            if user:
                if user.check_password(password=password):
                    login_user(user)
                    next = request.args.get('next')
                    return redirect(next or url_for('info.home'))
        flash('Invalid username/password combination')
        return redirect(url_for('auth.login'))
    # GET: Serve Log-in page
    return render_template('proteomescout/auth/login.html',
                           form=LoginForm()
                           )




@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """User sign-up page."""
    signup_form = SignupForm(request.form)
    # POST: Sign user in
    if request.method == 'POST':
        if signup_form.validate():
            # Get Form Fields
            username = request.form.get('username')
            
            password = request.form.get('password')
            name = request.form.get('name')
            email = request.form.get('email')

            institution = request.form.get('institution')
            existing_username = load_user_by_username(username)
            existing_email = load_user_by_email(email)
            if existing_username is None and existing_email is None:
                user = User(username=username,
                            name=name,
                            email=email,
                            institution=institution
                            )
                user.create_user(password)
                user.process_invitations()
                
                db.session.add(user)
                db.session.commit()
                login_user(user)
                
                return redirect(url_for('info.home'))
            if existing_email is not None:
                flash('A user already exists with that email address.')
            if existing_username is not None:
                flash('A user already exists with that username.')
            return redirect(url_for('auth.signup'))
        flash('Invalid sign-up')
        
    # GET: Serve Sign-up page
    return render_template('/proteomescout/auth/signup.html',
                           title='Create an Account',
                           form=signup_form,
                           template='signup-page',
                           body="Sign up for a user account.")


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))