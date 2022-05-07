import sqlalchemy
from .db_session import SqlAlchemyBase


class ActualPrices(SqlAlchemyBase):
    __tablename__ = 'actual_prices'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    metal = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    quantity = sqlalchemy.Column(sqlalchemy.Float, nullable=False)