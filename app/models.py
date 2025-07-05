from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Customer(db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String)
    phone = db.Column(db.String, nullable=False, unique=True)

    # Relación con eventos (1 cliente tiene muchos eventos)
    eventos = db.relationship('Evento', backref='customer', cascade='all, delete')

class Evento(db.Model):
    __tablename__ = 'eventos'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    titulo = db.Column(db.String, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
