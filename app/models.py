from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)  # Уникальный идентификатор пользователя
    email = Column(String, unique=True, index=True, nullable=False)  # Email пользователя, уникальный
    hashed_password = Column(String, nullable=False)  # Хэшированный пароль пользователя
    is_active = Column(Boolean, default=True)  # Флаг активности пользователя
    is_superuser = Column(Boolean, default=False)  # Флаг суперпользователя
    is_verified = Column(Boolean, default=False)  # Флаг подтверждения email
    role = Column(String, default="user")  # Роль пользователя: user, admin, superadmin
    first_name = Column(String, nullable=False)  # Имя пользователя
    last_name = Column(String, nullable=False)  # Фамилия пользователя
    middle_name = Column(String, nullable=True)  # Отчество пользователя
    phone_number = Column(String, nullable=False)  # Телефонный номер пользователя
    registration_date = Column(DateTime, default=datetime.utcnow)  # Дата регистрации пользователя
    block_date = Column(DateTime, nullable=True)  # Дата блокировки пользователя, null если не заблокирован


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    is_completed = Column(Boolean, default=False)
    items = relationship("OrderItem", back_populates="order")
    rfids = relationship("OrderRFID", back_populates="order")


class RFID(Base):
    __tablename__ = "rfids"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    is_valid = Column(Boolean, default=True)
    limit = Column(Boolean, default=False)
    last_used = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0)
    order_rfids = relationship("OrderRFID", back_populates="rfid")


class Terminal(Base):
    __tablename__ = "terminals"
    id = Column(Integer, primary_key=True, index=True)
    registration_date = Column(DateTime, default=datetime.utcnow)
    status_id = Column(Integer, ForeignKey('terminal_states.id'), default=1, nullable=False)
    serial = Column(String, unique=True)
    bottles = relationship("TerminalBottle", back_populates="terminal")
    status = relationship("TerminalState", back_populates="terminals")


class TerminalState(Base):
    __tablename__ = "terminal_states"
    id = Column(Integer, primary_key=True, index=True)
    state = Column(String, unique=True, index=True)
    terminals = relationship("Terminal", back_populates="status")


class TerminalBottle(Base):
    __tablename__ = "terminal_bottles"
    id = Column(Integer, primary_key=True, index=True)
    terminal_id = Column(Integer, ForeignKey("terminals.id"))
    bottle_id = Column(Integer, ForeignKey("bottles.id"), default=-1)
    slot_number = Column(Integer)  # Slot number (1-8) in the terminal
    remaining_volume = Column(Float)
    terminal = relationship("Terminal", back_populates="bottles")
    bottle = relationship("Bottle")


class Bottle(Base):
    __tablename__ = "bottles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    winery = Column(String)
    rating_average = Column(Float)
    location = Column(String)
    image_path300 = Column(String)
    image_path600 = Column(String)
    description = Column(String)
    wine_type = Column(String)
    volume = Column(Float)  # Total volume of the bottle


class BottleUsageLog(Base):
    __tablename__ = "bottle_usage_log"
    id = Column(Integer, primary_key=True, index=True)
    terminal_id = Column(Integer, ForeignKey("terminals.id"))
    bottle_id = Column(Integer, ForeignKey("bottles.id"))
    usage_date = Column(DateTime, default=datetime.utcnow)
    used_volume = Column(Float)


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    bottle_id = Column(Integer, ForeignKey("bottles.id"))
    volume = Column(Float)
    order = relationship("Order", back_populates="items")
    bottle = relationship("Bottle")


class OrderRFID(Base):
    __tablename__ = "order_rfids"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    rfid_id = Column(Integer, ForeignKey("rfids.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    order = relationship("Order", back_populates="rfids")
    rfid = relationship("RFID", back_populates="order_rfids")


EMPTY_BOTTLE_ID = -1
