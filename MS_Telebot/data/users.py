import sqlalchemy
from .db_session import SqlAlchemyBase


class User(SqlAlchemyBase):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, nullable=False)
    metal = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    price = sqlalchemy.Column(sqlalchemy.Float, nullable=False)
    client_amount = sqlalchemy.Column(sqlalchemy.Float, default=0, nullable=False)
    kush_recording = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    operation_ended = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    kush_percent = sqlalchemy.Column(sqlalchemy.Float, default=0, nullable=False)