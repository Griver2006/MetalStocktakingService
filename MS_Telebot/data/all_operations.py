import sqlalchemy
from .db_session import SqlAlchemyBase


class AllOperations(SqlAlchemyBase):
    __tablename__ = 'all_operations'

    date = sqlalchemy.Column(sqlalchemy.Date)
    time = sqlalchemy.Column(sqlalchemy.Time)
    metal = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    quantity = sqlalchemy.Column(sqlalchemy.Float, nullable=False)
    price = sqlalchemy.Column(sqlalchemy.Float, nullable=False)
    sum = sqlalchemy.Column(sqlalchemy.Float, nullable=False)
    comment = sqlalchemy.Column(sqlalchemy.String)
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)