from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import uuid, io, csv, os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .database import Base, engine, get_db
from .models import *
from .schemas import LoginRequest, CreateOrder, StockUpdate, PurchaseCreate
from .seed import seed

Base.metadata.create_all(bind=engine)
with next(get_db()) as db:
    seed(db)

app = FastAPI(title="Truflux FoodFlow API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

FRONTEND_DIST = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))

def current_user(db: Session, authorization: str | None):
    if not authorization:
        return None
    token = authorization.replace("Bearer", "").strip()
    s = db.query(SessionToken).filter(SessionToken.token == token).first()
    return s.user if s else None

def audit(db, action, actor="system", details=""):
    db.add(AuditLog(action=action, actor=actor, details=details)); db.commit()

@app.get("/api/health")
def health():
    return {"status":"OK", "message":"Truflux FoodFlow API is running", "version":"1.0.0"}

@app.post("/api/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    if payload.otp != "123456":
        raise HTTPException(401, "Invalid OTP. Prototype OTP is 123456.")
    user = db.query(User).filter(User.phone == payload.phone).first()
    if not user:
        user = User(phone=payload.phone, name=payload.name or "FoodFlow Customer", role="customer")
        db.add(user); db.commit(); db.refresh(user)
    token = str(uuid.uuid4())
    db.add(SessionToken(user_id=user.id, token=token)); db.commit()
    audit(db, "LOGIN", user.phone, "Mobile OTP login successful")
    return {"token": token, "user": {"id": user.id, "phone": user.phone, "name": user.name, "role": user.role}}

@app.get("/api/auth/me")
def me(authorization: str | None = Header(None), db: Session = Depends(get_db)):
    user = current_user(db, authorization)
    if not user:
        raise HTTPException(401, "Not logged in")
    return {"id": user.id, "phone": user.phone, "name": user.name, "role": user.role}

@app.get("/api/stores")
def stores(db: Session = Depends(get_db)):
    return db.query(Store).filter(Store.active == True).all()

@app.get("/api/menu")
def menu(store_id: int = 1, db: Session = Depends(get_db)):
    return db.query(MenuItem).filter(MenuItem.store_id == store_id, MenuItem.available == True).all()

@app.post("/api/orders")
def create_order(payload: CreateOrder, authorization: str | None = Header(None), db: Session = Depends(get_db)):
    user = current_user(db, authorization)
    order_no = "FF" + datetime.utcnow().strftime("%y%m%d%H%M%S") + str(uuid.uuid4())[:4].upper()
    total = 0
    order = Order(order_no=order_no, user_id=user.id if user else None, store_id=payload.store_id, source=payload.source, fulfillment=payload.fulfillment, payment_method=payload.payment_method, scheduled_for=payload.scheduled_for)
    db.add(order); db.commit(); db.refresh(order)
    for line in payload.items:
        item = db.query(MenuItem).filter(MenuItem.id == line.menu_item_id).first()
        if not item: continue
        total += item.price * line.qty
        db.add(OrderItem(order_id=order.id, menu_item_id=item.id, qty=line.qty, customization=line.customization, price=item.price))
        recipes = db.query(Recipe).filter(Recipe.menu_item_id == item.id).all()
        for rec in recipes:
            stock = db.query(Stock).filter(Stock.store_id == payload.store_id, Stock.ingredient_id == rec.ingredient_id).first()
            if stock:
                consume = rec.qty * line.qty
                stock.consumed_qty += consume
                stock.closing_qty = max(0, stock.closing_qty - consume)
    order.total = total
    db.commit(); db.refresh(order)
    audit(db, "ORDER_CREATED", user.phone if user else "walk-in", f"{order.order_no} via {payload.source}; ₹{total}")
    return {"order_no": order.order_no, "status": order.status, "payment_status": order.payment_status, "total": order.total}

@app.get("/api/orders")
def list_orders(store_id: int | None = None, status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Order).order_by(Order.created_at.desc())
    if store_id: q = q.filter(Order.store_id == store_id)
    if status: q = q.filter(Order.status == status)
    return q.limit(100).all()

@app.patch("/api/orders/{order_no}/status")
def update_order(order_no: str, status: str, db: Session = Depends(get_db)):
    o = db.query(Order).filter(Order.order_no == order_no).first()
    if not o: raise HTTPException(404, "Order not found")
    o.status = status; db.commit()
    audit(db, "ORDER_STATUS", "kitchen", f"{order_no} -> {status}")
    return {"ok": True, "order_no": order_no, "status": status}

@app.get("/api/inventory")
def inventory(store_id: int = 1, db: Session = Depends(get_db)):
    rows = db.query(Stock).filter(Stock.store_id == store_id).all()
    return [{"id":r.id,"store":r.store.name,"ingredient":r.ingredient.name,"unit":r.ingredient.unit,"opening_qty":r.opening_qty,"received_qty":r.received_qty,"consumed_qty":r.consumed_qty,"wastage_qty":r.wastage_qty,"closing_qty":r.closing_qty,"reorder_level":r.ingredient.reorder_level,"low_stock":r.closing_qty <= r.ingredient.reorder_level} for r in rows]

@app.post("/api/inventory/update")
def inventory_update(payload: StockUpdate, db: Session = Depends(get_db)):
    s = db.query(Stock).filter(Stock.store_id == payload.store_id, Stock.ingredient_id == payload.ingredient_id).first()
    if not s: raise HTTPException(404, "Stock row not found")
    s.received_qty += payload.received_qty
    s.consumed_qty += payload.consumed_qty
    s.wastage_qty += payload.wastage_qty
    s.closing_qty = s.closing_qty + payload.received_qty - payload.consumed_qty - payload.wastage_qty
    db.commit(); audit(db, "STOCK_UPDATED", "manager", f"Ingredient {payload.ingredient_id}")
    return {"ok": True}

@app.post("/api/procurement/indents")
def create_indent(payload: PurchaseCreate, db: Session = Depends(get_db)):
    p = PurchaseIndent(**payload.model_dump())
    db.add(p); db.commit(); db.refresh(p)
    audit(db, "PURCHASE_INDENT", "manager", f"Indent {p.id}")
    return p

@app.get("/api/procurement/indents")
def indents(db: Session = Depends(get_db)):
    return db.query(PurchaseIndent).order_by(PurchaseIndent.created_at.desc()).all()

@app.get("/api/analytics/summary")
def analytics(db: Session = Depends(get_db)):
    orders = db.query(Order).count()
    sales = db.query(func.coalesce(func.sum(Order.total), 0)).scalar()
    pending = db.query(Order).filter(Order.status.in_(["confirmed","preparing"])).count()
    stores = db.query(Store).count()
    low = 0
    for s in db.query(Stock).all():
        if s.closing_qty <= s.ingredient.reorder_level: low += 1
    by_source = db.query(Order.source, func.count(Order.id), func.coalesce(func.sum(Order.total),0)).group_by(Order.source).all()
    top_items = db.query(MenuItem.name, func.sum(OrderItem.qty).label('qty')).join(OrderItem, MenuItem.id==OrderItem.menu_item_id).group_by(MenuItem.name).order_by(func.sum(OrderItem.qty).desc()).limit(5).all()
    return {"orders":orders,"sales":sales,"pending":pending,"stores":stores,"low_stock":low,"by_source":[{"source":a,"orders":b,"sales":c} for a,b,c in by_source],"top_items":[{"name":a,"qty":b} for a,b in top_items]}

@app.get("/api/reports/custom")
def custom_report(format: str = "json", db: Session = Depends(get_db)):
    data = db.query(Order).order_by(Order.created_at.desc()).limit(200).all()
    rows = [[o.order_no, o.store.name, o.source, o.fulfillment, o.status, o.payment_status, o.total, o.created_at.isoformat()] for o in data]
    headers = ["Order No","Store","Source","Fulfillment","Status","Payment","Total","Created At"]
    if format == "csv":
        output = io.StringIO(); writer=csv.writer(output); writer.writerow(headers); writer.writerows(rows); output.seek(0)
        return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition":"attachment; filename=foodflow_report.csv"})
    if format == "pdf":
        buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=A4); y=800
        c.setFont("Helvetica-Bold", 16); c.drawString(40,y,"Truflux FoodFlow - Custom Operations Report"); y-=30
        c.setFont("Helvetica", 8)
        for r in [headers]+rows[:35]:
            c.drawString(40,y," | ".join(map(str,r))[:130]); y-=16
            if y < 40: c.showPage(); y=800; c.setFont("Helvetica",8)
        c.save(); buf.seek(0)
        return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition":"attachment; filename=foodflow_report.pdf"})
    return {"headers": headers, "rows": rows, "outputs": ["PDF", "Excel", "CSV", "Scheduled Email", "API Feed", "Dashboard Widget"]}

@app.get("/api/audit")
def logs(db: Session = Depends(get_db)):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()

if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")
    @app.get("/{full_path:path}")
    def spa(full_path: str):
        index = os.path.join(FRONTEND_DIST, "index.html")
        return FileResponse(index) if os.path.exists(index) else {"status":"API only"}
