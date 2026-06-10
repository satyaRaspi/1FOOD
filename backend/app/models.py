from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, default="Guest User")
    role = Column(String, default="customer")
    created_at = Column(DateTime, default=datetime.utcnow)

class SessionToken(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    token = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")

class Store(Base):
    __tablename__ = "stores"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    city = Column(String, default="Bangalore")
    state = Column(String, default="Karnataka")
    active = Column(Boolean, default=True)

class MenuItem(Base):
    __tablename__ = "menu_items"
    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id"))
    name = Column(String, nullable=False)
    category = Column(String, default="Food")
    description = Column(Text, default="")
    price = Column(Float, nullable=False)
    available = Column(Boolean, default=True)
    image = Column(String, default="")
    store = relationship("Store")

class Ingredient(Base):
    __tablename__ = "ingredients"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    unit = Column(String, default="kg")
    reorder_level = Column(Float, default=5)

class Stock(Base):
    __tablename__ = "stock"
    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id"))
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"))
    opening_qty = Column(Float, default=0)
    received_qty = Column(Float, default=0)
    consumed_qty = Column(Float, default=0)
    wastage_qty = Column(Float, default=0)
    closing_qty = Column(Float, default=0)
    store = relationship("Store")
    ingredient = relationship("Ingredient")

class Recipe(Base):
    __tablename__ = "recipes"
    id = Column(Integer, primary_key=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"))
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"))
    qty = Column(Float, default=0)
    menu_item = relationship("MenuItem")
    ingredient = relationship("Ingredient")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    order_no = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    store_id = Column(Integer, ForeignKey("stores.id"))
    source = Column(String, default="app")  # app, web, kiosk, pos
    fulfillment = Column(String, default="pickup")
    status = Column(String, default="confirmed")
    payment_status = Column(String, default="paid")
    payment_method = Column(String, default="UPI")
    total = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    scheduled_for = Column(String, default="Today")
    user = relationship("User")
    store = relationship("Store")
    items = relationship("OrderItem", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"))
    qty = Column(Integer, default=1)
    customization = Column(Text, default="")
    price = Column(Float, default=0)
    menu_item = relationship("MenuItem")

class PurchaseIndent(Base):
    __tablename__ = "purchase_indents"
    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id"))
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"))
    qty = Column(Float, default=0)
    status = Column(String, default="Raised")
    created_at = Column(DateTime, default=datetime.utcnow)
    store = relationship("Store")
    ingredient = relationship("Ingredient")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    action = Column(String)
    actor = Column(String, default="system")
    details = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
