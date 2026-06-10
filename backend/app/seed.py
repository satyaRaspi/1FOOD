from sqlalchemy.orm import Session
from .models import Store, MenuItem, Ingredient, Stock, Recipe, User

STORES = [
    ("Truflux Bengaluru Central Kitchen", "Bangalore", "Karnataka"),
    ("Vidhan Soudha Cafeteria", "Bangalore", "Karnataka"),
    ("MG Road Food Court", "Bangalore", "Karnataka"),
]
ING = [("Rice","kg",20),("Dosa Batter","litre",15),("Paneer","kg",8),("Dal","kg",10),("Vegetables","kg",12),("Oil","litre",8),("Packaging Box","nos",100),("Coffee Powder","kg",5)]
MENU = [
    ("Masala Dosa","South Indian","Crispy dosa with spiced potato filling",129,[('Dosa Batter',0.20),('Oil',0.02),('Packaging Box',1)]),
    ("Paneer Butter Masala","Indian","Rich cottage cheese curry",159,[('Paneer',0.12),('Vegetables',0.05),('Oil',0.02),('Packaging Box',1)]),
    ("Lemon Rice","South Indian","Rice with lemon and seasoning",109,[('Rice',0.18),('Oil',0.01),('Packaging Box',1)]),
    ("Dal Tadka Combo","Meals","Dal, rice, two phulkas and salad",150,[('Dal',0.12),('Rice',0.15),('Vegetables',0.05),('Packaging Box',1)]),
    ("Filter Coffee","Beverages","Fresh South Indian filter coffee",35,[('Coffee Powder',0.02)]),
]

def seed(db: Session):
    if db.query(Store).count() > 0:
        return
    stores=[]
    for n,c,s in STORES:
        st=Store(name=n, city=c, state=s); db.add(st); stores.append(st)
    db.commit()
    ingredients={}
    for n,u,r in ING:
        ing=Ingredient(name=n, unit=u, reorder_level=r); db.add(ing); ingredients[n]=ing
    db.commit()
    for store in stores:
        for ing in ingredients.values():
            db.add(Stock(store_id=store.id, ingredient_id=ing.id, opening_qty=100, received_qty=0, consumed_qty=0, wastage_qty=0, closing_qty=100))
    db.commit()
    for store in stores:
        for name,cat,desc,price,recipe in MENU:
            mi=MenuItem(store_id=store.id, name=name, category=cat, description=desc, price=price, available=True)
            db.add(mi); db.commit(); db.refresh(mi)
            for ing_name, qty in recipe:
                db.add(Recipe(menu_item_id=mi.id, ingredient_id=ingredients[ing_name].id, qty=qty))
    db.add(User(phone="9999999999", name="Admin User", role="admin"))
    db.add(User(phone="8888888888", name="Store Manager", role="manager"))
    db.commit()
