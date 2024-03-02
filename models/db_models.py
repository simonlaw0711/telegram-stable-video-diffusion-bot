# models/db_models.py
from sqlalchemy import Column, Integer, String, BigInteger, Enum, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.schema import Index

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=True, unique=True)
    name = Column(String(255), nullable=True)
    username = Column(String(255), unique=True)
    status = Column(Enum('VIP', 'Regular'), default='Regular')
    wallet_address = Column(String(255), nullable=True)
    is_subscribed = Column(Boolean, default=False)
    message_id = Column(BigInteger, nullable=True)
    update_count = Column(Integer, default=0)
    credit = Column(Integer, default=3)

    __table_args__ = (Index('idx_username','username'),)


