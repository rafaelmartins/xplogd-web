# coding: utf-8

from datetime import datetime, timedelta

from flask import Flask, Response, abort, jsonify, request
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config.setdefault('TITLE', 'XPLOGD Web')
app.config.setdefault('AUTH_USERNAME', 'username')
app.config.setdefault('AUTH_PASSWORD', 'password')
app.config.setdefault('AIRCRAFT_SEEN_GAP_SECONDS', 30)
app.config.setdefault('SQLALCHEMY_DATABASE_URI', 'sqlite:////tmp/test.db')
app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)
app.config.from_envvar('XPLOGD_WEB_CONFIG', True)

db = SQLAlchemy(app)
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)


class Aircraft(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    icao_type = db.Column(db.String(50))
    registration = db.Column(db.String(50))

    @classmethod
    def get_or_create(cls, icao_type, registration):
        rv = cls.query.filter_by(icao_type=icao_type,
                                 registration=registration).first()
        if rv is None:
            return cls(icao_type=icao_type, registration=registration)
        return rv

    def to_json(self):
        return {
            'icao_type': self.icao_type,
            'registration': self.registration,
        }

    def __str__(self):
        return '%s (%s)' % (self.registration, self.icao_type)

    def __repr__(self):
        return '<Aircraft: %s>' % self


class Position(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    aircraft_id = db.Column(db.Integer, db.ForeignKey(Aircraft.id),
                            nullable=False)
    aircraft = db.relationship('Aircraft', backref='flights',
                               foreign_keys=[aircraft_id])
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    altitude = db.Column(db.Integer)
    track = db.Column(db.Integer)
    ground_speed = db.Column(db.Integer)
    air_speed = db.Column(db.Integer)
    vertical_speed = db.Column(db.Integer)

    @staticmethod
    def meters_to_feets(l):
        return int(float(l) * 3.28084)

    @staticmethod
    def meters_per_second_to_knots(l):
        return int(float(l) * 1.94384)

    @staticmethod
    def meters_per_second_to_feets_per_minute(l):
        return int(float(l) * 196.85)

    @classmethod
    def create_from_xplogd(cls, data):
        pieces = data.split('\n')
        if len(pieces) != 11:
            return None

        # check protocol version and trailing newline
        if pieces[0] != '1' or pieces[10] != '':
            return None

        return cls(
            aircraft=Aircraft.get_or_create(pieces[1], pieces[2]),
            latitude=float(pieces[3]),
            longitude=float(pieces[4]),
            altitude=cls.meters_to_feets(pieces[5]),
            track=int(float(pieces[6])),
            ground_speed=cls.meters_per_second_to_knots(pieces[7]),
            air_speed=cls.meters_per_second_to_knots(pieces[8]),
            vertical_speed=cls.meters_per_second_to_feets_per_minute(
                pieces[9]
            )
        )

    @classmethod
    def get_active_position(cls):
        delta = timedelta(seconds=app.config['AIRCRAFT_SEEN_GAP_SECONDS'])
        return cls.query.filter(
            cls.time >= datetime.utcnow() - delta
        ).order_by(cls.time.desc()).first()

    def to_json(self):
        aircraft = None
        if self.aircraft is not None:
            aircraft = self.aircraft.to_json()
        return {
            'aircraft': aircraft,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'altitude': self.altitude,
            'track': self.track,
            'ground_speed': self.ground_speed,
            'air_speed': self.air_speed,
            'vertical_speed': self.vertical_speed,
        }

    def __str__(self):
        return '%s lat=%f; lon=%f; alt=%d' % (self.aircraft,
                                              self.latitude,
                                              self.longitude,
                                              self.altitude)

    def __repr__(self):
        return '<Position: %s>' % self


@app.route('/tracking/', methods=['POST'])
def tracking():
    if request.authorization is None or \
       request.authorization.username != app.config['AUTH_USERNAME'] or \
       request.authorization.password != app.config['AUTH_PASSWORD']:
        return Response(
            status=401,
            headers={'WWW-Authenticate': 'Basic realm="xplogd-web"'}
        )

    mime = request.headers.get('content-type')
    if mime != 'application/vnd.xplogd.serialized':
        return '', 400

    pos = Position.create_from_xplogd(request.data)
    db.session.add(pos)
    db.session.commit()

    return '', 202


@app.route('/live/')
def live():
    active = Position.get_active_position()
    if active is None:
        abort(404)

    return jsonify(active.to_json())


if __name__ == '__main__':
    manager.run()
