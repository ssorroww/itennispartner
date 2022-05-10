#!/usr/bin/env python3

import os

import flask
from flask import Flask
from flask import render_template
from flask import request
from flask import abort, redirect, url_for
import flask_login
from .db import get_db
import datetime


login_manager = flask_login.LoginManager()
users = {'sasha': {'password': 'secret'}}

class User(flask_login.UserMixin):
    pass

@login_manager.user_loader
def user_loader(email):
    if email not in users:
        return

    user = User()
    user.id = email
    return user


@login_manager.request_loader
def request_loader(request):
    email = request.form.get('email')
    if email not in users:
        return

    user = User()
    user.id = email
    return user

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'database.sqlite'),
    )

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from . import db
    db.init_app(app)

    login_manager.init_app(app)

    @app.route('/login', methods=['POST'])
    def login():
        phone = flask.request.form['phone']
        if phone in users and flask.request.form['password'] == users[phone]['password']:
            user = User()
            user.id = phone
            flask_login.login_user(user)
            flask.flash('Logged in successfully.')
            return flask.redirect(flask.url_for('client'))

        return 'Bad login'

    @app.route('/client')
    @flask_login.login_required
    def client():
        return render_template('client.html', user=flask_login.current_user)

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/sportsmen/update')
    def sportsmen_update():
        return "не доделал"

    @app.route('/sportsmen')
    def sportsmen():
        cx = get_db()
        cu = cx.cursor()
        return render_template('sportsmen.html', sportsmen={ 'list': cu.execute('select * from players') })

    @app.route('/clubs')
    def clubs():
        cx = get_db()
        cu = cx.cursor()
        clubs = { 'list': cu.execute('select * from clubs') }
        return render_template('clubs.html', clubs=clubs)

    @app.route('/clubs/<id>/schedule')
    def club_schedule(id):
        cx = get_db()
        cu = cx.cursor()

        date = flask.request.args.get('date')
        if not date:
            date = datetime.date.today().strftime('%Y-%m-%d')

        schedule = {}
        for place in cu.execute(f'select * from places where club_id=?', (id)):
            schedule[place['id']] = {'info': place, 'timetable': []}

        for tt in cu.execute(f'select tt.* from timetable as tt join places as p on (p.id=tt.place_id) where tt.datetime like ? and p.club_id=?', (f'{date}%', id)):
            schedule[tt['place_id']]['timetable'].append(tt)

        club = {
            'info': cu.execute('select * from clubs where id=?', (id)).fetchall()[0],
            'date': date,
            'sportsmen': cu.execute('select * from players').fetchall(),
            'schedule': schedule.values(),
        }

        return render_template('club_schedule.html', club=club)

    @app.route('/clubs/<id>/places')
    def club_places(id):
        cx = get_db()
        cu = cx.cursor()
        try:
            club = {
                'info': cu.execute('select * from clubs where id=?', (id)).fetchall()[0],
                'places': cu.execute('select * from places where club_id=?', (id)).fetchall(),
            }

            return render_template('club_places.html', club=club)
        except:
            return flask.redirect(flask.url_for('clubs'))

    @app.route('/clubs/<id>/places/create')
    def club_places_create(id):
        cx = get_db()
        cu = cx.cursor()
        name = flask.request.args.get('name')
        cu.execute('insert into places (name, club_id) values (?, ?)', (name, id))
        cx.commit()
        return flask.redirect(flask.url_for('club_places', id=id))

    @login_manager.unauthorized_handler
    def unauthorized_handler():
        return 'Unauthorized', 401

    return app
