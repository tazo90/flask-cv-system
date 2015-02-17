#coding: utf-8
import os
from collections import OrderedDict

from flask import Flask, render_template, request
from flask import json
from flask_sqlalchemy import SQLAlchemy
from werkzeug.routing import BaseConverter

# forms
from flask.ext.wtf import Form
from wtforms import TextField, PasswordField, validators, HiddenField
from wtforms import TextAreaField, BooleanField
from wtforms.validators import Required, EqualTo, Optional
from wtforms.validators import Length, Email

# login
from flask.ext.login import LoginManager, login_user, logout_user
from flask.ext.login import current_user, login_required
from flask import redirect, url_for, session


application = Flask(__name__)
application.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('OPENSHIFT_POSTGRESQL_DB_URL') if os.environ.get('OPENSHIFT_POSTGRESQL_DB_URL') else 'postgresql://tazo:pchela@localhost:5432/cv'
# forms config
application.config['CSRF_ENABLED'] = True
application.config['SECRET_KEY'] = 'pchela'

db = SQLAlchemy(application)

# login init
login_manager = LoginManager()
login_manager.init_app(application)
login_manager.login_view = '/login'
@login_manager.user_loader
def load_user(id):
    return Users.query.get(int(id))

# DB
class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(60), unique=True)
    description = db.Column(db.Text)
    tags = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __init__(self, title = None, description = None, tags = None):
        self.title = title
        self.description = description
        self.tags = tags

    def _asdict(self):
        result = OrderedDict()
        for key in self.__mapper__.c.keys():
            result[key] = getattr(self, key)
        return result


class Users(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(60), unique=True)
    firstname = db.Column(db.String(20))
    lastname = db.Column(db.String(20))
    password = db.Column(db.String)
    email = db.Column(db.String(100), unique=True)
    
    time_registered = db.Column(db.DateTime)
    tagline = db.Column(db.String(255))
    bio = db.Column(db.Text)
    avatar = db.Column(db.String(255))
    active = db.Column(db.Boolean)
    portfolio = db.relationship('Portfolio')

    def __init__(self, username=None, password=None, email=None,
        firstname=None, lastname=None, tagline=None, bio=None,
        avatar=None):
        self.username = username
        self.email = email
        self.firstname = firstname
        self.lastname = lastname
        self.password = password
        self.tagline = tagline
        self.bio = bio
        self.avatar = avatar

    def is_authenticated(self):
        return True

    def is_active(self):
        return self.active

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

    def __repr__(self):
        return '<User: %s>' % (self.username)

class RegexConverter(BaseConverter):
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]

application.url_map.converters['regex'] = RegexConverter
#@application.route('/<regex("[abcABC0-9]{4,6}"):uid>-<slug>/')

# Forms
class SignupForm(Form):
    username = TextField(u'Nazwa użytkownika',
        validators=[Required(u'Musisz wpisać nazwę użytkownika')])
    password = PasswordField(u'Hasło',
        validators=[Required(u'Musisz wpisać hasło'),
                    Length(min=6, message=(u'Hasło musi mieć co najmniej 6 znaków'))])
    email = TextField(u'Email',
        validators=[Required(u'Wpisz adres email'),
                    Length(min=6, message=(u'Adres email zbyt krótki')),
                    Email(message=(u'Błędny adres email'))])
    agree = BooleanField(u'Akceptuję warunki <a href="#">korzystania z serwisu</a>',
        validators=[Required(u'Musisz zaakceptować warunki korzystania z serwisu')])

class SigninForm(Form):
    username = TextField(u'Nazwa użytkownika',
        validators=[Required(),
            Length(min=3, message=(u'Nazwa użytkownika musi mieć co najmniej 3 znaki')) ])
    password = PasswordField(u'Hasło',
        validators=[Required(),
            Length(min=6, message=(u'Proszę podaj dłuższe hasło')) ])
    remember_me = BooleanField(u'Zapamiętaj mnie', default=False)

class PortfolioForm(Form):
    title = TextField(u'Tytuł',
        validators=[Required(u'Musisz podać tytuł swojego portfolio')])
    description = TextField(u'Opis',
        validators=[Required(u'Musisz uzupełnić opis')])
    tags = TextField(u'Tagi')

@application.route('/')
def index():
    return render_template('themes/water/index.html',
        page_title=u'Udostępnij swoje CV pracodawcy - Twoje-CV.pl',
        signin_form = SigninForm() )


@application.route('/profil/', methods=['GET', 'POST'])
@application.route('/profil/<username>/', methods=['GET', 'POST'])
def profile(username = None):
    #print 'req ', request
    if request.method == 'POST':
        print 'req ', dir(request.form)
        print request.form

    if username is None:
        return render_template('themes/water/search_profile.html',
            page_title=u'Znajdź odpowiedniego pracownika')

    user = Users.query.filter_by(username=username).first()

    if user is None:
        user = Users()
        user.username = username
        user.firstname = 'Batman, to Ty?'
        user.lastname = ''
        user.tagline = 'Specjalne'
        user.bio = 'Brak'
        user.avatar = '../../static/img/default-avatar.png'

        return render_template('themes/water/profile.html',
            page_title = 'Ups! ' + user.firstname,
            user = user,
            signin_form = SigninForm(),
            portfolio_form = PortfolioForm() )
    return render_template('themes/water/profile.html',
        page_title = 'Twoje-CV.pl - ' + user.firstname + ' ' + user.lastname,
        user = user,
        signin_form = SigninForm(),
        portfolio_form = PortfolioForm())

@application.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if current_user is not None and current_user.is_authenticated():
            return redirect(url_for('profil', username=current_user))

        form = SigninForm(request.form)
        if form.validate_on_submit():
            user = Users.query.filter_by(username = form.username.data).first()
            if user is None:
                form.username.errors.append(u'Użytkownik nie istnieje')
                return render_template('themes/water/login.html',
                                        signin_form = form)

            if user.password != form.password.data:
                form.password.errors.append(u'Błędny hasło')
                return render_template('themes/water/signin.html',
                                        signin_form = form)

            login_user(user, remember = form.remember_me.data)
            session['signed'] = True
            session['username'] = user.username

            if session.get('next'):
                next_page = session.get('next')
                session.pop('next')
                return redirect(next_page)
            else:
                return redirect(url_for('profile', username=session['username']))
        return render_template('themes/water/login.html',
                                    signin_form = form)
    else:
        session['next'] = request.args.get('next')
        return render_template('themes/water/login.html',
                                page_title = 'Twoje-CV.pl - Logowanie',
                                signin_form = SigninForm() )

@application.route('/logout')
def logout():
    session.pop('signed')
    session.pop('username')
    logout_user()
    return redirect(url_for('index'))

@application.route('/rejestracja/', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        form = SignupForm(request.form)
        if form.validate():
            user = Users()
            form.populate_obj(user) # fill table by form data
            
            user_exist = Users.query.filter_by(username=form.username.data).first()
            email_exist = Users.query.filter_by(email=form.email.data).first()

            if user_exist:
                form.username.errors.append(u'Nazwa użytkownika jest zajęta')
            
            if email_exist:
                form.email.errors.append(u'Email jest zajęty')


            if user_exist or email_exist:
                return render_template('themes/water/signup.html',
                    form = form, page_title = "Twoje-CV.pl - Rejestracja")
            else:
                user.firstname = 'Imie'
                user.lastname = 'Nazwisko'
                user.tagline = u'Twoje umiejętności'
                user.bio = u'Wyjaśnij reszcie świata jak bardzo unikatową osobą jesteś'
                user.avatar = '../../static/img/default-avatar.png'

                db.session.add(user)
                db.session.commit()
                return render_template('themes/water/signup-success.html',
                    user = user, page_title = u'Rejestracja zakończona pomyślnie')

        else:
            return render_template('themes/water/signup.html',
                form = form,
                page_title = u'Twoje-CV.pl - Rejestracja')
    return render_template('themes/water/signup.html',
        form = SignupForm(),
        page_title = u'Utwórz swoje CV')

# AJAX/JSON
@application.route('/portfolio_get/<id>')
#@login_required
def portfolio_get(id):
    portfolio = Portfolio.query.get(id)
    return json.dumps(portfolio._asdict())

@application.route('/portfolio_delete/<id>')
#@login_required
def portfolio_delete(id):
    portfolio = Portfolio.query.get(id)
    db.session.delete(portfolio)
    db.session.commit()
    result = {}
    result['result'] = 'success'
    return json.dumps(result)

def dbinit():
    db.drop_all()
    db.create_all()
    user1 = Users(username='tazo', firstname='Mariusz', lastname='Winnik',\
        password='test', email='tazo@o2.pl', tagline='Django/Python Programmer',\
        bio='I love python very much', avatar='../../static/img/face.jpg')
    user1.portfolio.append(Portfolio(title='tazoCMS', description='CMS in django', tags='jQuery, Django, PostgreSQL, Bootstrap, Ajax'))
    user1.portfolio.append(Portfolio(title='Certifacate portal', description='Certificate web system in Django', tags='Django, jQuery'))
    db.session.add(user1)

    user = Users(username='diesel', firstname='Diesel', lastname='Piotr',
        password='pchela', email="dieselo@o2.pl")
    user.portfolio.append(Portfolio(title='FikrPOS', description='An integrated POS solution'))
    db.session.commit()

if __name__ == '__main__':
    dbinit();
    application.run(debug=True, host="0.0.0.0", port=8000)
