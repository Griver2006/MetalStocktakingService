import sqlalchemy
from .db_session import SqlAlchemyBase


class ButtonsCleanWeights(SqlAlchemyBase):
    __tablename__ = 'buttons_clean_weights'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name_clean_weight = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    description_clean_w = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    path = sqlalchemy.Column(sqlalchemy.String, nullable=False)