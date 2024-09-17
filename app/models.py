import datetime

from sqlalchemy import (Column, Integer, String, Boolean, ForeignKey, DateTime, Float)
from sqlalchemy.orm import (relationship)
from sqlalchemy.ext.declarative import (declarative_base)

Base = declarative_base()


class User(Base):
    """
    User model.

    This model represents a user account in the system.

    Attributes:
        id (int): The unique identifier of the user.
        email (str): The email address of the user.
        hashed_password (str): The hashed password of the user.
        is_active (bool): A flag indicating whether the user is active.
        is_superuser (bool): A flag indicating whether the user is a superuser.
        is_verified (bool): A flag indicating whether the user's email is verified.
        role (str): The role of the user.
        first_name (str): The first name of the user.
        last_name (str): The last name of the user.
        middle_name (str): The middle name of the user.
        phone_number (str): The phone number of the user.
        registration_date (datetime): The date and time when the user registered.
        block_date (datetime|None): The date and time when the user was blocked (if any).

    """
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
    registration_date = Column(DateTime, default=datetime.datetime.utcnow())  # Дата регистрации пользователя
    block_date = Column(DateTime, nullable=True)  # Дата блокировки пользователя, null если не заблокирован


class Order(Base):
    """
    Order model.

    This model represents an order in the system.

    Attributes:
        id (int): The unique identifier of the order.
        is_completed (bool): A flag indicating whether the order is completed.
        items (list[OrderItem]): A list of items in the order.
        rfids (list[OrderRFID]): A list of RFIDs in the order.

    """
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    is_completed = Column(Boolean, default=False)
    items = relationship("OrderItem", back_populates="order")
    rfids = relationship("OrderRFID", back_populates="order")


class RFID(Base):
    """
    RFID model.

    This model represents an RFID tag in the system.

    Attributes:
        id (int): The unique identifier of the RFID tag.
        code (str): The code of the RFID tag.
        is_valid (bool): A flag indicating whether the RFID tag is valid.
        limit (bool): A flag indicating whether the RFID tag is limited.
        last_used (datetime): The date and time when the RFID tag was last used.
        usage_count (int): The number of times the RFID tag has been used.

    """
    __tablename__ = "rfids"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, index=True)
    is_valid = Column(Boolean, default=True)
    limit = Column(Boolean, default=False)
    last_used = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0)
    order_rfids = relationship("OrderRFID", back_populates="rfid")


class Terminal(Base):
    """
    Terminal model.

    This model represents a terminal in the system.

    Attributes:
        id (int): The unique identifier of the terminal.
        registration_date (datetime): The date and time when the terminal was registered.
        status_id (int): The identifier of the status of the terminal.
        serial (str): The unique serial number of the terminal.
        bottles (list[TerminalBottle]): A list of bottles in the terminal.
        status (TerminalState): The status of the terminal.

    """
    __tablename__ = "terminals"
    id = Column(Integer, primary_key=True, index=True)
    registration_date = Column(DateTime, default=datetime.datetime.utcnow())
    status_id = Column(Integer, ForeignKey('terminal_states.id'), default=1, nullable=False)
    serial = Column(String, unique=True)
    bottles = relationship("TerminalBottle", back_populates="terminal")
    status = relationship("TerminalState", back_populates="terminals")


class TerminalState(Base):
    """
    TerminalState model.

    This model represents a state of a terminal in the system.

    Attributes:
        id (int): The unique identifier of the state.
        state (str): The name of the state.
        terminals (list[Terminal]): A list of terminals in the state.

    """
    __tablename__ = "terminal_states"
    id = Column(Integer, primary_key=True, index=True)
    state = Column(String, unique=True, index=True)
    terminals = relationship("Terminal", back_populates="status")


class TerminalBottle(Base):
    """
    TerminalBottle model.

    This model represents a bottle in the terminal.

    Attributes:
        id (int): The unique identifier of the bottle.
        terminal_id (int): The identifier of the terminal the bottle belongs to.
        slot_number (int): The slot number of the bottle in the terminal.
        remaining_volume (float): The remaining volume of the bottle in the terminal.
        bottle_id (int): The identifier of the bottle.

    """
    __tablename__ = "terminal_bottles"
    id = Column(Integer, primary_key=True, index=True)
    terminal_id = Column(Integer, ForeignKey("terminals.id"))
    bottle_id = Column(Integer, ForeignKey("bottles.id"), default=-1)
    slot_number = Column(Integer)  # Slot number (1-8) in the terminal
    remaining_volume = Column(Float)
    terminal = relationship("Terminal", back_populates="bottles")
    bottle = relationship("Bottle")


class Bottle(Base):
    """
    Bottle model.

    This model represents a bottle in the system.

    Attributes:
        id (int): The unique identifier of the bottle.
        name (str): The name of the bottle.
        winery (str): The winery of the bottle.
        rating_average (int): The average rating of the bottle.
        location (str): The location of the bottle.
        image_path300 (str): The path to the image of the bottle.
        image_path600 (str): The path to the image of the bottle.
        description (str): The description of the bottle.
        wine_type (str): The type of wine of the bottle.
        volume (int): The volume of the bottle.
    """
    __tablename__ = "bottles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    winery = Column(String)
    rating_average = Column(Integer)
    location = Column(String)
    image_path300 = Column(String)
    image_path600 = Column(String)
    description = Column(String)
    wine_type = Column(String)
    volume = Column(Integer)  # Total volume of the bottle


class BottleUsageLog(Base):
    """
    BottleUsageLog model.

    This model represents a log of bottle usage in the system.

    Attributes:
        id (int): The unique identifier of the log.
        terminal_id (int): The identifier of the terminal the log belongs to.
        bottle_id (int): The identifier of the bottle the log represents.
        usage_date (datetime): The date and time when the log was created.
        used_volume (float): The volume of the bottle used in the log.
    """
    __tablename__ = "bottle_usage_log"
    id = Column(Integer, primary_key=True, index=True)
    terminal_id = Column(Integer, ForeignKey("terminals.id"))
    bottle_id = Column(Integer, ForeignKey("bottles.id"))
    usage_date = Column(DateTime, default=datetime.datetime.utcnow())
    used_volume = Column(Float)


class OrderItem(Base):
    """
    OrderItem model.

    This model represents an item in an order.

    Attributes:
        id (int): The unique identifier of the item.
        order_id (int): The identifier of the order the item belongs to.
        bottle_id (int): The identifier of the bottle the item represents.
        volume (float): The volume of the item.
        order (Order): The order the item belongs to.
        bottle (Bottle): The bottle the item represents.
        timestamp (datetime): The timestamp of the item.
    """
    __tablename__ = "order_item"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    bottle_id = Column(Integer, ForeignKey("bottles.id"))
    volume = Column(Float)
    order = relationship("Order", back_populates="items")
    bottle = relationship("Bottle")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow())


class OrderRFID(Base):
    """
    OrderRFID model.

    This model represents an RFID tag in an order.

    Attributes:
        id (int): The unique identifier of the RFID tag.
        order_id (int): The identifier of the order the RFID tag belongs to.
        rfid_id (int): The identifier of the RFID tag.
        timestamp (datetime): The timestamp of the RFID tag.
        order (Order): The order the RFID tag belongs to.
        rfid (RFID): The RFID tag.
    """
    __tablename__ = "order_rfids"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    rfid_id = Column(Integer, ForeignKey("rfids.id"))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow())
    order = relationship("Order", back_populates="rfids")
    rfid = relationship("RFID", back_populates="order_rfids")


class WarehouseBottle(Base):
    """
    WarehouseBottle model.

    This model represents a bottle stored in the warehouse.

    Attributes:
        id (int): The unique identifier of the warehouse bottle entry.
        bottle_id (int): The identifier of the bottle.
        quantity (int): The quantity of this bottle in the warehouse.
        current_in_terminals (int): The current quantity of this bottle in terminals.
    """
    __tablename__ = "warehouse_bottles"
    id = Column(Integer, primary_key=True, index=True)
    bottle_id = Column(Integer, ForeignKey("bottles.id"))
    quantity = Column(Integer)  # Количество бутылок на складе
    current_in_terminals = Column(Integer, default=0)  # Количество бутылок в терминалах

    bottle = relationship("Bottle")