import sqlalchemy
from .db_session import SqlAlchemyBase


class MinusOperations(SqlAlchemyBase):
    __tablename__ = 'minus_operations'

    metal = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    quantity = sqlalchemy.Column(sqlalchemy.Float, nullable=False)
    price = sqlalchemy.Column(sqlalchemy.Float, nullable=False)
    sum = sqlalchemy.Column(sqlalchemy.Float, nullable=False)
    date = sqlalchemy.Column(sqlalchemy.Date, nullable=False)
    task = sqlalchemy.Column(sqlalchemy.String)
    wher = sqlalchemy.Column(sqlalchemy.String)
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)