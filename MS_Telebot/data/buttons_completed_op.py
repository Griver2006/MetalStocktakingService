import sqlalchemy
from .db_session import SqlAlchemyBase


class ButtonsCompletedOp(SqlAlchemyBase):
    __tablename__ = 'buttons_completed_op'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    date = sqlalchemy.Column(sqlalchemy.Date)
    time = sqlalchemy.Column(sqlalchemy.Time)
    metal = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    weight_from_sys = sqlalchemy.Column(sqlalchemy.Float, nullable=False)
    weight_true = sqlalchemy.Column(sqlalchemy.Float, nullable=False)
    color = sqlalchemy.Column(sqlalchemy.String)