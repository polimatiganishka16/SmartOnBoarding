from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.Integer, default=0)
    last_active = db.Column(db.Integer, default=0)
    avatar_color = db.Column(db.String(20), default='#6366f1')

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.Integer, nullable=False)

class ABTest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, unique=True)
    variant = db.Column(db.String(10))

class UserProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, unique=True, nullable=False)
    current_step = db.Column(db.Integer, default=1)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.Integer)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    message = db.Column(db.String(500), nullable=False)
    read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.Integer, nullable=False)
    notif_type = db.Column(db.String(50), default='info')
