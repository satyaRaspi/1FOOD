from pydantic import BaseModel
from typing import List, Optional

class LoginRequest(BaseModel):
    phone: str
    otp: str = "123456"
    name: Optional[str] = None

class OrderLine(BaseModel):
    menu_item_id: int
    qty: int
    customization: str = ""

class CreateOrder(BaseModel):
    store_id: int
    source: str = "app"
    fulfillment: str = "pickup"
    payment_method: str = "UPI"
    scheduled_for: str = "Today"
    items: List[OrderLine]

class StockUpdate(BaseModel):
    store_id: int
    ingredient_id: int
    received_qty: float = 0
    consumed_qty: float = 0
    wastage_qty: float = 0

class PurchaseCreate(BaseModel):
    store_id: int
    ingredient_id: int
    qty: float
