import sqlite3, json, os, secrets, math, datetime, hashlib
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'foodflow.sqlite3')
VERSION = '1.1.14'

app = FastAPI(title='Truflux FoodFlow', version=VERSION)
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])


def now():
    return datetime.datetime.now().isoformat(timespec='seconds')

def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def rows(cur):
    return [dict(r) for r in cur.fetchall()]

def jdump(x):
    return json.dumps(x, ensure_ascii=False)

def jload(x, default=None):
    if not x:
        return default if default is not None else []
    try: return json.loads(x)
    except Exception: return default if default is not None else []

def token_hash(token: str):
    return hashlib.sha256(token.encode()).hexdigest()[:16]

def get_user_by_token(token: str):
    with conn() as c:
        r = c.execute('select u.* from sessions s join users u on u.id=s.user_id where s.token=?', (token,)).fetchone()
        return dict(r) if r else None

def require_admin(token: str):
    u = get_user_by_token(token)
    if not u or u.get('role') not in ('super_admin','store_admin','cashier','kitchen','central_kitchen'):
        raise HTTPException(403, 'Admin/staff access required')
    return u

class MobileIn(BaseModel):
    mobile: str

class OTPIn(BaseModel):
    mobile: str
    otp: str
    name: Optional[str] = None

class ProfileIn(BaseModel):
    token: str
    name: Optional[str] = ''
    email: Optional[str] = ''
    photo_url: Optional[str] = ''
    address: Optional[str] = ''
    dietary_preferences: Optional[str] = ''
    preferred_store_id: Optional[int] = None

class OrderItem(BaseModel):
    item_id: int
    quantity: int
    customisation: Optional[str] = ''

class CreateOrderIn(BaseModel):
    token: Optional[str] = None
    mobile: Optional[str] = None
    store_id: int
    source: str = 'mobile'
    items: List[OrderItem]
    payment_method: str = 'UPI'
    pickup_slot: Optional[str] = 'now'
    notes: Optional[str] = ''
    apply_offer_code: Optional[str] = None

class PaymentIn(BaseModel):
    order_id: int
    payment_status: str = 'success'
    gateway_ref: Optional[str] = None

class StatusIn(BaseModel):
    order_id: int
    status: str

class MenuItemIn(BaseModel):
    token: str
    name: str
    sku: str
    category: str
    price: float
    image_url: Optional[str] = ''
    description: Optional[str] = ''
    store_id: Optional[int] = None
    is_combo: bool = False
    cross_sell_ids: Optional[List[int]] = []
    upsell_ids: Optional[List[int]] = []
    enabled: bool = True
    out_of_stock: bool = False

class MenuUpdateIn(MenuItemIn):
    id: int

class ThemeIn(BaseModel):
    token: str
    primary_color: str
    secondary_color: str
    accent_color: str
    background_color: str
    app_name: str
    logo_url: Optional[str] = ''
    ad_banner_url: Optional[str] = ''
    app_banner_url: Optional[str] = ''
    kiosk_banner_url: Optional[str] = ''
    ad_banner_title: Optional[str] = ''
    ad_banner_text: Optional[str] = ''

class FeatureIn(BaseModel):
    token: str
    features: Dict[str, Any]

class TaxIn(BaseModel):
    token: str
    taxes: Dict[str, Any]

class ValidateQRIn(BaseModel):
    token: str
    qr_token: str


TEST_MENU_CATALOG = {
    'Breakfast': [
        ('Idli Plate','SKU-IDLI',40,'https://images.unsplash.com/photo-1668236543090-82eba5ee5976?auto=format&fit=crop&w=600&q=80','Soft idlis with chutney and sambar'),
        ('Masala Dosa','SKU-DOSA',85,'https://images.unsplash.com/photo-1694849789325-914b71ab4075?auto=format&fit=crop&w=600&q=80','Crisp dosa with potato masala'),
        ('Medu Vada','SKU-VADA',35,'https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?auto=format&fit=crop&w=600&q=80','Crispy vada with chutney'),
        ('Vegetable Upma','SKU-UPMA',55,'https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=600&q=80','Warm semolina breakfast bowl'),
        ('Pongal','SKU-PONGAL',60,'https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=600&q=80','Comfort pongal with ghee and pepper')
    ],
    'Meals': [
        ('Lemon Rice','SKU-LEMON-RICE',70,'https://images.unsplash.com/photo-1596797038530-2c107229654b?auto=format&fit=crop&w=600&q=80','Fresh lemon rice meal bowl'),
        ('Curd Rice','SKU-CURD-RICE',65,'https://images.unsplash.com/photo-1596560548464-f010549b84d7?auto=format&fit=crop&w=600&q=80','Comfort curd rice bowl'),
        ('Veg Biryani','SKU-VEG-BIRYANI',120,'https://images.unsplash.com/photo-1563379091339-03246963d96c?auto=format&fit=crop&w=600&q=80','Aromatic vegetable biryani'),
        ('Chapati Meal','SKU-CHAPATI-MEAL',95,'https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=600&q=80','Chapati with curry and dal'),
        ('Sambar Rice','SKU-SAMBAR-RICE',80,'https://images.unsplash.com/photo-1512058564366-18510be2db19?auto=format&fit=crop&w=600&q=80','Hot sambar rice bowl')
    ],
    'Snacks': [
        ('Samosa','SKU-SAMOSA',25,'https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=600&q=80','Crisp evening snack'),
        ('Vada Pav','SKU-VADA-PAV',45,'https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?auto=format&fit=crop&w=600&q=80','Spicy vada pav'),
        ('Onion Pakora','SKU-PAKORA',50,'https://images.unsplash.com/photo-1562967916-eb82221dfb36?auto=format&fit=crop&w=600&q=80','Hot pakoras for tea time'),
        ('Veg Sandwich','SKU-SANDWICH',75,'https://images.unsplash.com/photo-1528735602780-2552fd46c7af?auto=format&fit=crop&w=600&q=80','Grilled vegetable sandwich'),
        ('Veg Cutlet','SKU-CUTLET',55,'https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?auto=format&fit=crop&w=600&q=80','Crispy veg cutlet')
    ],
    'Beverages': [
        ('Filter Coffee','SKU-COFFEE',30,'https://images.unsplash.com/photo-1509042239860-f550ce710b93?auto=format&fit=crop&w=600&q=80','Fresh filter coffee'),
        ('Fresh Juice','SKU-JUICE',60,'https://images.unsplash.com/photo-1600271886742-f049cd451bba?auto=format&fit=crop&w=600&q=80','Seasonal fresh juice'),
        ('Masala Tea','SKU-TEA',20,'https://images.unsplash.com/photo-1571934811356-5cc061b6821f?auto=format&fit=crop&w=600&q=80','Hot masala tea'),
        ('Buttermilk','SKU-BUTTERMILK',25,'https://images.unsplash.com/photo-1544145945-f90425340c7e?auto=format&fit=crop&w=600&q=80','Chilled spiced buttermilk'),
        ('Sweet Lassi','SKU-LASSI',50,'https://images.unsplash.com/photo-1622597467836-f3285f2131b8?auto=format&fit=crop&w=600&q=80','Refreshing sweet lassi')
    ],
    'Combos': [
        ('South Indian Meal Combo','SKU-MEAL-COMBO',140,'https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=600&q=80','Rice, curry, sambar, curd and sweet'),
        ('Breakfast Combo','SKU-BREAKFAST-COMBO',120,'https://images.unsplash.com/photo-1694849789325-914b71ab4075?auto=format&fit=crop&w=600&q=80','Idli, vada and coffee combo'),
        ('Snack Combo','SKU-SNACK-COMBO',90,'https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=600&q=80','Samosa with tea combo'),
        ('Family Meal Combo','SKU-FAMILY-MEAL',420,'https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=600&q=80','Family-size meal bundle'),
        ('Kids Combo','SKU-KIDS-COMBO',110,'https://images.unsplash.com/photo-1528735602780-2552fd46c7af?auto=format&fit=crop&w=600&q=80','Sandwich, juice and snack combo')
    ]
}

def seed_test_menu_data(actor_mobile: str = 'system'):
    inserted = 0
    updated = 0
    with conn() as c:
        stores = rows(c.execute('select id from stores where active=1 order by id'))
        for st in stores:
            sid = st['id']
            for category, items in TEST_MENU_CATALOG.items():
                for name, sku, price, image_url, desc in items:
                    existing = c.execute('select id from menu_items where store_id=? and sku=?', (sid, sku)).fetchone()
                    if existing:
                        c.execute('''update menu_items set name=?, category=?, price=?, image_url=?, description=?, enabled=1, out_of_stock=0 where id=?''',
                                  (name, category, price, image_url, desc, existing['id']))
                        updated += 1
                    else:
                        is_combo = 1 if category == 'Combos' else 0
                        c.execute('''insert into menu_items(store_id,name,sku,category,price,image_url,description,is_combo,cross_sell_ids,upsell_ids,enabled,out_of_stock,created_at)
                        values(?,?,?,?,?,?,?,?,?,?,?,?,?)''', (sid, name, sku, category, price, image_url, desc, is_combo, '[]', '[]', 1, 0, now()))
                        inserted += 1
        c.execute('insert into audit_logs(actor,action,details,created_at) values(?,?,?,?)',
                  (actor_mobile, 'TEST_DATA_CREATED', f'Inserted {inserted}, refreshed {updated}; five items per category across active stores', now()))
        c.commit()
    return {'inserted': inserted, 'updated': updated, 'categories': list(TEST_MENU_CATALOG.keys()), 'items_per_category': 5, 'stores_updated': len(stores)}

def init_db():
    with conn() as c:
        c.executescript('''
        create table if not exists users(
            id integer primary key autoincrement, mobile text unique, name text, email text, photo_url text,
            address text, dietary_preferences text, preferred_store_id integer, role text default 'consumer', created_at text
        );
        create table if not exists sessions(id integer primary key autoincrement, user_id integer, token text unique, created_at text);
        create table if not exists otps(mobile text primary key, otp text, created_at text);
        create table if not exists stores(id integer primary key autoincrement, name text, area text, city text, state text, lat real, lng real, active integer default 1);
        create table if not exists menu_items(
            id integer primary key autoincrement, store_id integer, name text, sku text, category text, price real,
            image_url text, description text, is_combo integer default 0, cross_sell_ids text, upsell_ids text,
            enabled integer default 1, out_of_stock integer default 0, created_at text
        );
        create table if not exists orders(
            id integer primary key autoincrement, order_no text unique, user_id integer, mobile text, store_id integer, source text,
            subtotal real, discount real, tax_total real default 0, tax_breakdown text, total real, payment_method text, payment_status text, order_status text,
            pickup_slot text, notes text, qr_token text unique, qr_status text, gateway_ref text, created_at text, updated_at text
        );
        create table if not exists order_items(
            id integer primary key autoincrement, order_id integer, item_id integer, sku text, name text, quantity integer,
            unit_price real, line_total real, customisation text
        );
        create table if not exists payments(id integer primary key autoincrement, order_id integer, amount real, method text, status text, gateway_ref text, created_at text);
        create table if not exists offers(id integer primary key autoincrement, code text, name text, description text, discount_type text, value real, enabled integer default 1);
        create table if not exists app_config(key text primary key, value text);
        create table if not exists audit_logs(id integer primary key autoincrement, actor text, action text, details text, created_at text);
        ''')
        # lightweight migrations for older local SQLite files
        for ddl in [
            'alter table orders add column tax_total real default 0',
            'alter table orders add column tax_breakdown text'
        ]:
            try:
                c.execute(ddl)
            except sqlite3.OperationalError:
                pass
        # seed only once
        if c.execute('select count(*) from stores').fetchone()[0] == 0:
            stores = [
                ('Truflux FoodFlow - MG Road','MG Road','Bangalore','Karnataka',12.9756,77.6066),
                ('Truflux FoodFlow - Indiranagar','Indiranagar','Bangalore','Karnataka',12.9719,77.6412),
                ('Truflux FoodFlow - Whitefield','Whitefield','Bangalore','Karnataka',12.9698,77.7500),
                ('Truflux FoodFlow - Koramangala','Koramangala','Bangalore','Karnataka',12.9352,77.6245)
            ]
            c.executemany('insert into stores(name,area,city,state,lat,lng) values(?,?,?,?,?,?)', stores)
        if c.execute('select count(*) from menu_items').fetchone()[0] == 0:
            sample = [
                (1,'Idli Plate','SKU-IDLI','Breakfast',40,'https://images.unsplash.com/photo-1668236543090-82eba5ee5976?auto=format&fit=crop&w=600&q=80','Soft idlis with chutney and sambar',0,'[6]','[8]',1,0),
                (1,'Masala Dosa','SKU-DOSA','Breakfast',85,'https://images.unsplash.com/photo-1694849789325-914b71ab4075?auto=format&fit=crop&w=600&q=80','Crisp dosa with potato masala',0,'[8]','[5]',1,0),
                (1,'Lemon Rice','SKU-LEMON-RICE','Meals',70,'https://images.unsplash.com/photo-1596797038530-2c107229654b?auto=format&fit=crop&w=600&q=80','Fresh lemon rice meal bowl',0,'[6]','[7]',1,0),
                (1,'Curd Rice','SKU-CURD-RICE','Meals',65,'https://images.unsplash.com/photo-1596560548464-f010549b84d7?auto=format&fit=crop&w=600&q=80','Comfort curd rice bowl',0,'[6]','[7]',1,0),
                (1,'South Indian Meal Combo','SKU-MEAL-COMBO','Combos',140,'https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=600&q=80','Rice, curry, sambar, curd and sweet',1,'[8]','[]',1,0),
                (1,'Filter Coffee','SKU-COFFEE','Beverages',30,'https://images.unsplash.com/photo-1509042239860-f550ce710b93?auto=format&fit=crop&w=600&q=80','Fresh filter coffee',0,'[]','[]',1,0),
                (1,'Fresh Juice','SKU-JUICE','Beverages',60,'https://images.unsplash.com/photo-1600271886742-f049cd451bba?auto=format&fit=crop&w=600&q=80','Seasonal fresh juice',0,'[]','[]',1,0),
                (1,'Samosa','SKU-SAMOSA','Snacks',25,'https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=600&q=80','Crisp evening snack',0,'[6]','[]',1,0)
            ]
            c.executemany('''insert into menu_items(store_id,name,sku,category,price,image_url,description,is_combo,cross_sell_ids,upsell_ids,enabled,out_of_stock)
            values(?,?,?,?,?,?,?,?,?,?,?,?)''', sample)
            # copy same menu to other stores with same SKU and name
            base = c.execute('select * from menu_items where store_id=1').fetchall()
            for sid in [2,3,4]:
                for r in base:
                    c.execute('''insert into menu_items(store_id,name,sku,category,price,image_url,description,is_combo,cross_sell_ids,upsell_ids,enabled,out_of_stock)
                    values(?,?,?,?,?,?,?,?,?,?,?,?)''', (sid,r['name'],r['sku'],r['category'],r['price'],r['image_url'],r['description'],r['is_combo'],r['cross_sell_ids'],r['upsell_ids'],1,0))
        if c.execute('select count(*) from users where mobile=?', ('9999999999',)).fetchone()[0] == 0:
            c.execute('insert into users(mobile,name,email,photo_url,address,dietary_preferences,preferred_store_id,role,created_at) values(?,?,?,?,?,?,?,?,?)',
                      ('9999999999','Admin User','admin@trufluxtech.com','', 'Bangalore, Karnataka','Vegetarian',1,'super_admin',now()))
        if c.execute('select count(*) from offers').fetchone()[0] == 0:
            c.execute('insert into offers(code,name,description,discount_type,value,enabled) values(?,?,?,?,?,?)', ('WELCOME10','Welcome Offer','10% discount on demo orders','percent',10,1))
        defaults = {
            'theme': {'primary_color':'#12103f','secondary_color':'#f4b942','accent_color':'#27ae60','background_color':'#f7f8fc','app_name':'Truflux FoodFlow','logo_url':'','ad_banner_url':'https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?auto=format&fit=crop&w=1200&q=80','app_banner_url':'','kiosk_banner_url':'','ad_banner_title':'Fresh Combos Today','ad_banner_text':'Tap a dish tile to add. Pay and collect using your QR receipt.'},
            'taxes': {'enabled': True, 'lines': [{'label':'GST','rate':5.0,'enabled':True}, {'label':'Other Tax','rate':0.0,'enabled':False}]},
            'features': {
                'mobile_ordering': True, 'kiosk_ordering': True, 'cashier_ordering': True, 'guest_kiosk_checkout': True,
                'otp_login': True, 'advance_ordering': True, 'pickup_slots': True, 'closest_store': True,
                'payment_gateway': True, 'pay_at_counter': True, 'qr_generation': True, 'qr_printing': True,
                'qr_sharing': True, 'kitchen_board': True, 'central_kitchen_sku_report': True, 'offers': True,
                'combos': True, 'cross_sell': True, 'upsell': True, 'ai_demand_prediction': True,
                'ai_reporting': True, 'theme_configuration': True, 'user_profile': True, 'notifications': True
            }
        }
        for k,v in defaults.items():
            if not c.execute('select value from app_config where key=?',(k,)).fetchone():
                c.execute('insert into app_config(key,value) values(?,?)',(k,jdump(v)))
        c.commit()

init_db()

@app.get('/')
@app.get('/landing')
@app.get('/home')
def landing():
    return FileResponse(os.path.join(BASE_DIR,'static','index.html'))

@app.get('/health')
@app.get('/api/health')
def health():
    return {'status':'OK','message':'Truflux FoodFlow API is running','version':VERSION}

@app.get('/app')
@app.get('/admin')
@app.get('/kiosk')
@app.get('/cashier')
@app.get('/delivery')
def webapp():
    return FileResponse(os.path.join(BASE_DIR,'static','index.html'))

app.mount('/static', StaticFiles(directory=os.path.join(BASE_DIR,'static')), name='static')

@app.post('/api/auth/send-otp')
def send_otp(inp: MobileIn):
    otp = '123456'
    with conn() as c:
        c.execute('insert or replace into otps(mobile,otp,created_at) values(?,?,?)',(inp.mobile,otp,now()))
        c.commit()
    return {'ok':True,'message':'OTP sent successfully. Demo OTP is 123456','demo_otp':otp}

@app.post('/api/auth/verify')
def verify(inp: OTPIn):
    if inp.otp != '123456':
        raise HTTPException(400, 'Invalid OTP. Demo OTP is 123456')
    with conn() as c:
        r = c.execute('select * from users where mobile=?',(inp.mobile,)).fetchone()
        if not r:
            c.execute('insert into users(mobile,name,email,photo_url,address,dietary_preferences,preferred_store_id,role,created_at) values(?,?,?,?,?,?,?,?,?)',
                      (inp.mobile, inp.name or f'User {inp.mobile[-4:]}', '', '', 'Bangalore, Karnataka', '', 1, 'consumer', now()))
            uid = c.execute('select last_insert_rowid()').fetchone()[0]
        else:
            uid = r['id']
        token = secrets.token_urlsafe(32)
        c.execute('insert into sessions(user_id,token,created_at) values(?,?,?)',(uid,token,now()))
        c.commit()
        user = dict(c.execute('select * from users where id=?',(uid,)).fetchone())
    return {'ok':True,'token':token,'user':user}

@app.get('/api/me')
def me(token: str):
    u = get_user_by_token(token)
    if not u: raise HTTPException(401,'Invalid session')
    return {'user':u}

@app.post('/api/logout')
def logout(token: str):
    with conn() as c:
        c.execute('delete from sessions where token=?',(token,))
        c.commit()
    return {'ok':True}

@app.post('/api/profile')
def profile(inp: ProfileIn):
    u = get_user_by_token(inp.token)
    if not u: raise HTTPException(401,'Invalid session')
    with conn() as c:
        c.execute('''update users set name=?,email=?,photo_url=?,address=?,dietary_preferences=?,preferred_store_id=? where id=?''',
                  (inp.name,inp.email,inp.photo_url,inp.address,inp.dietary_preferences,inp.preferred_store_id,u['id']))
        c.commit()
    return {'ok':True,'user':get_user_by_token(inp.token)}

@app.get('/api/stores')
def stores(lat: Optional[float]=None, lng: Optional[float]=None):
    with conn() as c:
        data = rows(c.execute('select * from stores where active=1'))
    if lat is not None and lng is not None:
        for s in data:
            R=6371
            dlat=math.radians(s['lat']-lat); dlng=math.radians(s['lng']-lng)
            a=math.sin(dlat/2)**2 + math.cos(math.radians(lat))*math.cos(math.radians(s['lat']))*math.sin(dlng/2)**2
            s['distance_km']=round(2*R*math.asin(math.sqrt(a)),2)
        data.sort(key=lambda x:x.get('distance_km',9999))
    return {'stores':data,'closest':data[0] if data else None}

@app.get('/api/menu')
def menu(store_id: int=1):
    with conn() as c:
        data = rows(c.execute('select * from menu_items where store_id=? and enabled=1 order by category,name',(store_id,)))
    for x in data:
        x['cross_sell_ids']=jload(x.get('cross_sell_ids'),'[]')
        x['upsell_ids']=jload(x.get('upsell_ids'),'[]')
    return {'items':data,'categories':sorted(list({x['category'] for x in data}))}

@app.get('/api/offers')
def offers():
    with conn() as c: return {'offers': rows(c.execute('select * from offers where enabled=1'))}

@app.post('/api/orders')
def create_order(inp: CreateOrderIn):
    user=None
    if inp.token:
        user=get_user_by_token(inp.token)
    if not user and not inp.mobile and inp.source != 'kiosk':
        raise HTTPException(401,'Login required or mobile number required')
    mobile = user['mobile'] if user else (inp.mobile or 'GUEST')
    user_id = user['id'] if user else None
    with conn() as c:
        item_rows=[]; subtotal=0.0
        for it in inp.items:
            r = c.execute('select * from menu_items where id=? and enabled=1',(it.item_id,)).fetchone()
            if not r: raise HTTPException(400,f'Item not found: {it.item_id}')
            if r['out_of_stock']: raise HTTPException(400,f'{r["name"]} is out of stock')
            qty=max(1,it.quantity)
            line=float(r['price'])*qty
            subtotal += line
            item_rows.append((r,qty,line,it.customisation or ''))
        discount=0.0
        if inp.apply_offer_code:
            offer=c.execute('select * from offers where code=? and enabled=1',(inp.apply_offer_code.upper(),)).fetchone()
            if offer:
                discount = subtotal*(float(offer['value'])/100.0) if offer['discount_type']=='percent' else float(offer['value'])
        taxable=max(0, subtotal-discount)
        tax_cfg=jload(c.execute('select value from app_config where key="taxes"').fetchone()['value'], {'enabled':False,'lines':[]})
        tax_lines=[]; tax_total=0.0
        if tax_cfg.get('enabled', True):
            for t in tax_cfg.get('lines', []):
                if t.get('enabled', True):
                    rate=float(t.get('rate') or 0)
                    amt=round(taxable*rate/100.0,2)
                    if amt or rate:
                        tax_lines.append({'label':t.get('label','Tax'), 'rate':rate, 'amount':amt})
                        tax_total += amt
        tax_total=round(tax_total,2)
        total=max(0, round(taxable+tax_total,2))
        order_no=f'TF-{inp.store_id}-{datetime.datetime.now().strftime("%y%m%d")}-{secrets.randbelow(9000)+1000}'
        qr_token=f'{order_no}|{token_hash(order_no+mobile+str(total))}'
        c.execute('''insert into orders(order_no,user_id,mobile,store_id,source,subtotal,discount,tax_total,tax_breakdown,total,payment_method,payment_status,order_status,pickup_slot,notes,qr_token,qr_status,created_at,updated_at)
        values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (order_no,user_id,mobile,inp.store_id,inp.source,subtotal,discount,tax_total,jdump(tax_lines),total,inp.payment_method,'pending','payment_pending',inp.pickup_slot,inp.notes,qr_token,'generated',now(),now()))
        oid = c.execute('select last_insert_rowid()').fetchone()[0]
        for r,qty,line,custom in item_rows:
            c.execute('insert into order_items(order_id,item_id,sku,name,quantity,unit_price,line_total,customisation) values(?,?,?,?,?,?,?,?)',
                      (oid,r['id'],r['sku'],r['name'],qty,r['price'],line,custom))
        c.execute('insert into audit_logs(actor,action,details,created_at) values(?,?,?,?)',(mobile,'ORDER_CREATED',order_no,now()))
        c.commit()
    return get_order(oid)

@app.get('/api/orders/{order_id}')
def get_order(order_id: int):
    with conn() as c:
        r = c.execute('select o.*, s.name as store_name, s.area as store_area from orders o join stores s on s.id=o.store_id where o.id=?',(order_id,)).fetchone()
        if not r: raise HTTPException(404,'Order not found')
        d=dict(r); d['items']=rows(c.execute('select * from order_items where order_id=?',(order_id,)))
        d['tax_breakdown']=jload(d.get('tax_breakdown'), [])
    return {'order':d}


@app.get('/api/orders/{order_id}/qr.png')
def order_qr_png(order_id: int):
    """Return a real scannable QR image for the order number."""
    with conn() as c:
        r = c.execute('select order_no from orders where id=?', (order_id,)).fetchone()
        if not r:
            raise HTTPException(404, 'Order not found')
        order_no = r['order_no']
    try:
        import io
        import qrcode
        img = qrcode.make(order_no)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return Response(content=buf.getvalue(), media_type='image/png')
    except Exception as e:
        raise HTTPException(500, f'QR generation failed: {e}')

@app.post('/api/payments/confirm')
def pay(inp: PaymentIn):
    with conn() as c:
        r=c.execute('select * from orders where id=?',(inp.order_id,)).fetchone()
        if not r: raise HTTPException(404,'Order not found')
        status = 'success' if inp.payment_status in ('success','paid') else inp.payment_status
        order_status = 'confirmed' if status=='success' else 'payment_failed'
        gateway_ref = inp.gateway_ref or f'PG-{secrets.randbelow(999999)}'
        c.execute('insert into payments(order_id,amount,method,status,gateway_ref,created_at) values(?,?,?,?,?,?)',(inp.order_id,r['total'],r['payment_method'],status,gateway_ref,now()))
        c.execute('update orders set payment_status=?, order_status=?, gateway_ref=?, updated_at=? where id=?',(status,order_status,gateway_ref,now(),inp.order_id))
        c.execute('insert into audit_logs(actor,action,details,created_at) values(?,?,?,?)',(r['mobile'],'PAYMENT_'+status.upper(),r['order_no'],now()))
        c.commit()
    return get_order(inp.order_id)

@app.get('/api/my-orders')
def my_orders(token: str):
    u=get_user_by_token(token)
    if not u: raise HTTPException(401,'Invalid session')
    with conn() as c:
        data=rows(c.execute('select o.*, s.name as store_name from orders o join stores s on s.id=o.store_id where o.user_id=? order by o.id desc',(u['id'],)))
        for d in data:
            d['items']=rows(c.execute('select * from order_items where order_id=?',(d['id'],)))
            d['tax_breakdown']=jload(d.get('tax_breakdown'), [])
    return {'orders':data}

@app.get('/api/kitchen-board')
def kitchen_board(store_id: Optional[int]=None):
    q='''select o.*, s.name as store_name from orders o join stores s on s.id=o.store_id where o.payment_status='success' and o.order_status not in ('completed','cancelled','delivered','fulfilled')'''
    params=[]
    if store_id:
        q+=' and o.store_id=?'; params.append(store_id)
    q+=' order by o.created_at asc'
    with conn() as c:
        data=rows(c.execute(q,params))
        for d in data:
            d['items']=rows(c.execute('select sku,name,quantity,customisation from order_items where order_id=?',(d['id'],)))
    return {'orders':data}

@app.post('/api/orders/status')
def set_status(inp: StatusIn):
    allowed={'confirmed','accepted','preparing','ready','delivered','completed','fulfilled','cancelled'}
    if inp.status not in allowed: raise HTTPException(400,'Invalid status')
    with conn() as c:
        c.execute('update orders set order_status=?, updated_at=? where id=?',(inp.status,now(),inp.order_id))
        c.commit()
    return get_order(inp.order_id)

@app.post('/api/qr/validate')
def validate_qr(inp: ValidateQRIn):
    require_admin(inp.token)
    with conn() as c:
        r=c.execute('select * from orders where qr_token=? or order_no=?',(inp.qr_token, inp.qr_token)).fetchone()
        if not r: return {'ok':False,'message':'Invalid QR token'}
        d=dict(r)
        if d['payment_status']!='success': return {'ok':False,'message':'Payment not confirmed','order':d}
        if d['order_status'] in ('delivered','completed','fulfilled'): return {'ok':False,'message':'Order already fulfilled','order':d}
        c.execute('update orders set order_status=?, qr_status=?, updated_at=? where id=?',('fulfilled','validated',now(),d['id']))
        c.commit()
    return {'ok':True,'message':'QR validated. Order marked fulfilled.','order':get_order(d['id'])['order']}


@app.post('/api/admin/test-data/menu')
def create_test_menu_data(token: str):
    u = require_admin(token)
    result = seed_test_menu_data(u['mobile'])
    return {'ok': True, 'message': 'Test menu data created/refreshed: five items in each category for every active store.', **result}

@app.get('/api/admin/menu')
def admin_menu(token: str, store_id: Optional[int]=None):
    require_admin(token)
    q='select * from menu_items'; params=[]
    if store_id: q+=' where store_id=?'; params.append(store_id)
    q+=' order by store_id,category,name'
    with conn() as c: return {'items':rows(c.execute(q,params))}

@app.post('/api/admin/menu')
def add_menu(inp: MenuItemIn):
    u=require_admin(inp.token)
    with conn() as c:
        c.execute('''insert into menu_items(store_id,name,sku,category,price,image_url,description,is_combo,cross_sell_ids,upsell_ids,enabled,out_of_stock,created_at)
        values(?,?,?,?,?,?,?,?,?,?,?,?,?)''', (inp.store_id or 1, inp.name, inp.sku, inp.category, inp.price, inp.image_url, inp.description, int(inp.is_combo), jdump(inp.cross_sell_ids or []), jdump(inp.upsell_ids or []), int(inp.enabled), int(inp.out_of_stock), now()))
        c.execute('insert into audit_logs(actor,action,details,created_at) values(?,?,?,?)',(u['mobile'],'MENU_ADD',inp.name,now()))
        c.commit()
    return {'ok':True}

@app.put('/api/admin/menu')
def upd_menu(inp: MenuUpdateIn):
    u=require_admin(inp.token)
    with conn() as c:
        c.execute('''update menu_items set store_id=?,name=?,sku=?,category=?,price=?,image_url=?,description=?,is_combo=?,cross_sell_ids=?,upsell_ids=?,enabled=?,out_of_stock=? where id=?''',
                  (inp.store_id or 1,inp.name,inp.sku,inp.category,inp.price,inp.image_url,inp.description,int(inp.is_combo),jdump(inp.cross_sell_ids or []),jdump(inp.upsell_ids or []),int(inp.enabled),int(inp.out_of_stock),inp.id))
        c.execute('insert into audit_logs(actor,action,details,created_at) values(?,?,?,?)',(u['mobile'],'MENU_UPDATE',inp.name,now()))
        c.commit()
    return {'ok':True}

@app.delete('/api/admin/menu/{item_id}')
def del_menu(item_id: int, token: str):
    u=require_admin(token)
    with conn() as c:
        c.execute('update menu_items set enabled=0 where id=?',(item_id,))
        c.execute('insert into audit_logs(actor,action,details,created_at) values(?,?,?,?)',(u['mobile'],'MENU_REMOVE',str(item_id),now()))
        c.commit()
    return {'ok':True}

@app.get('/api/admin/dashboard')
def dashboard(token: str):
    require_admin(token)
    with conn() as c:
        stats = {
            'orders_today': c.execute("select count(*) from orders where date(created_at)=date('now')").fetchone()[0],
            'sales_today': round(c.execute("select coalesce(sum(total),0) from orders where payment_status='success' and date(created_at)=date('now')").fetchone()[0],2),
            'pending_kitchen': c.execute("select count(*) from orders where payment_status='success' and order_status not in ('completed','delivered','cancelled')").fetchone()[0],
            'mobile_orders': c.execute("select count(*) from orders where source='mobile'").fetchone()[0],
            'kiosk_orders': c.execute("select count(*) from orders where source='kiosk'").fetchone()[0],
            'cashier_orders': c.execute("select count(*) from orders where source='cashier'").fetchone()[0]
        }
        by_store = rows(c.execute('''select s.name store, count(o.id) orders, coalesce(sum(o.total),0) sales from stores s left join orders o on o.store_id=s.id group by s.id order by s.id'''))
    return {'stats':stats,'by_store':by_store}

@app.get('/api/admin/sku-report')
def sku_report(token: str, day: Optional[str]=None):
    require_admin(token)
    day = day or datetime.date.today().isoformat()
    with conn() as c:
        data = rows(c.execute('''select oi.sku, oi.name, s.name as store, sum(oi.quantity) as quantity, count(distinct o.id) as order_count
        from order_items oi join orders o on o.id=oi.order_id join stores s on s.id=o.store_id
        where o.payment_status='success' and date(o.created_at)=date(?)
        group by oi.sku, oi.name, s.id order by oi.sku, s.name''',(day,)))
        totals = rows(c.execute('''select oi.sku, oi.name, sum(oi.quantity) as total_quantity
        from order_items oi join orders o on o.id=oi.order_id where o.payment_status='success' and date(o.created_at)=date(?) group by oi.sku, oi.name order by total_quantity desc''',(day,)))
    return {'day':day,'by_store':data,'totals':totals}

@app.get('/api/admin/sku-report.csv')
def sku_csv(token: str):
    data = sku_report(token)['by_store']
    out='SKU,Item,Store,Quantity,Order Count\n'
    for r in data:
        out += f'{r["sku"]},{r["name"]},{r["store"]},{r["quantity"]},{r["order_count"]}\n'
    return Response(out, media_type='text/csv', headers={'Content-Disposition':'attachment; filename=sku_report.csv'})

@app.get('/api/ai/insights')
def ai_insights(token: Optional[str]=None, store_id: Optional[int]=None):
    # prototype AI: rule-based predictions from order history + menu popularity
    with conn() as c:
        popular=rows(c.execute('''select oi.sku, oi.name, sum(oi.quantity) qty from order_items oi join orders o on o.id=oi.order_id where o.payment_status='success' group by oi.sku,oi.name order by qty desc limit 5'''))
        items=rows(c.execute('select sku,name,category,out_of_stock from menu_items where enabled=1 limit 8'))
        orders=c.execute('select count(*) from orders where payment_status="success"').fetchone()[0]
    demand = 'moderate' if orders < 10 else 'high'
    recs = []
    if popular:
        recs.append(f'Prepare additional stock for {popular[0]["name"]}; it is currently the leading SKU.')
    recs.append('Use coffee / beverage as a cross-sell with breakfast items.')
    recs.append('Create time-based combos during low-demand hours to improve kitchen utilization.')
    recs.append('Advance orders should be locked into the SKU report for central kitchen planning.')
    forecast=[]
    for i,x in enumerate(items[:5]):
        forecast.append({'sku':x['sku'], 'item':x['name'], 'predicted_qty_tomorrow': max(10, 25 - i*3 + orders)})
    return {'demand_level':demand,'popular_items':popular,'recommendations':recs,'tomorrow_forecast':forecast,'model':'Prototype AI rules + historical demand baseline'}

@app.get('/api/config')
def config():
    with conn() as c:
        theme=jload(c.execute('select value from app_config where key="theme"').fetchone()['value'],{})
        features=jload(c.execute('select value from app_config where key="features"').fetchone()['value'],{})
        tr=c.execute('select value from app_config where key="taxes"').fetchone()
        taxes=jload(tr['value'], {'enabled':True,'lines':[]}) if tr else {'enabled':True,'lines':[]}
    return {'theme':theme,'features':features,'taxes':taxes}

@app.post('/api/admin/theme')
def set_theme(inp: ThemeIn):
    require_admin(inp.token)
    theme=inp.dict(); theme.pop('token')
    with conn() as c:
        c.execute('insert or replace into app_config(key,value) values(?,?)',('theme',jdump(theme)))
        c.commit()
    return {'ok':True,'theme':theme}

@app.post('/api/admin/features')
def set_features(inp: FeatureIn):
    require_admin(inp.token)
    with conn() as c:
        c.execute('insert or replace into app_config(key,value) values(?,?)',('features',jdump(inp.features)))
        c.commit()
    return {'ok':True,'features':inp.features}

@app.post('/api/admin/taxes')
def set_taxes(inp: TaxIn):
    require_admin(inp.token)
    with conn() as c:
        c.execute('insert or replace into app_config(key,value) values(?,?)',('taxes',jdump(inp.taxes)))
        c.commit()
    return {'ok':True,'taxes':inp.taxes}



@app.get('/api/admin/central-kitchen-demand')
def central_kitchen_demand(token: str, from_date: Optional[str]=None, to_date: Optional[str]=None, store_id: Optional[int]=None):
    # Date-wise and location-wise menu demand report for central kitchen production planning.
    require_admin(token)
    from_date = from_date or datetime.date.today().isoformat()
    to_date = to_date or from_date
    params = [from_date, to_date]
    store_filter = ''
    if store_id:
        store_filter = ' and o.store_id=? '
        params.append(store_id)
    with conn() as c:
        rows_detail = rows(c.execute(f'''select date(o.created_at) as demand_date,
            s.id as store_id, s.name as store_name, s.area as location,
            oi.sku, oi.name as item_name, coalesce(mi.category,'') as category,
            sum(oi.quantity) as demand_qty,
            count(distinct o.id) as order_count,
            round(sum(oi.line_total),2) as gross_value
        from order_items oi
        join orders o on o.id=oi.order_id
        join stores s on s.id=o.store_id
        left join menu_items mi on mi.id=oi.item_id
        where o.payment_status='success'
          and date(o.created_at) between date(?) and date(?) {store_filter}
        group by date(o.created_at), s.id, oi.sku, oi.name
        order by demand_date desc, s.area, oi.name''', params))
        by_date = rows(c.execute(f'''select date(o.created_at) as demand_date,
            sum(oi.quantity) as demand_qty,
            count(distinct o.id) as order_count,
            round(sum(oi.line_total),2) as gross_value
        from order_items oi join orders o on o.id=oi.order_id
        where o.payment_status='success' and date(o.created_at) between date(?) and date(?) {store_filter}
        group by date(o.created_at) order by demand_date desc''', params))
        by_location = rows(c.execute(f'''select s.id as store_id, s.name as store_name, s.area as location,
            sum(oi.quantity) as demand_qty,
            count(distinct o.id) as order_count,
            round(sum(oi.line_total),2) as gross_value
        from order_items oi join orders o on o.id=oi.order_id join stores s on s.id=o.store_id
        where o.payment_status='success' and date(o.created_at) between date(?) and date(?) {store_filter}
        group by s.id order by s.area''', params))
        by_item = rows(c.execute(f'''select oi.sku, oi.name as item_name, coalesce(mi.category,'') as category,
            sum(oi.quantity) as demand_qty,
            count(distinct o.id) as order_count,
            round(sum(oi.line_total),2) as gross_value
        from order_items oi join orders o on o.id=oi.order_id left join menu_items mi on mi.id=oi.item_id
        where o.payment_status='success' and date(o.created_at) between date(?) and date(?) {store_filter}
        group by oi.sku, oi.name order by demand_qty desc''', params))
        stores = rows(c.execute('select id,name,area from stores where active=1 order by area'))
    grand = {
        'demand_qty': sum(int(r.get('demand_qty') or 0) for r in rows_detail),
        'order_count': sum(int(r.get('order_count') or 0) for r in by_date),
        'gross_value': round(sum(float(r.get('gross_value') or 0) for r in rows_detail), 2)
    }
    production_plan = []
    for r in by_item[:12]:
        qty = int(r.get('demand_qty') or 0)
        buffer_qty = max(1, math.ceil(qty * 0.10)) if qty else 0
        production_plan.append({
            'sku': r.get('sku'),
            'item_name': r.get('item_name'),
            'category': r.get('category'),
            'confirmed_qty': qty,
            'suggested_buffer_qty': buffer_qty,
            'suggested_cook_qty': qty + buffer_qty
        })
    return {'from_date': from_date, 'to_date': to_date, 'store_id': store_id, 'stores': stores,
            'detail': rows_detail, 'by_date': by_date, 'by_location': by_location, 'by_item': by_item,
            'grand': grand, 'production_plan': production_plan,
            'note': 'Central kitchen should use confirmed paid order demand by date, location and SKU for cooking plan.'}

@app.get('/api/admin/central-kitchen-demand.csv')
def central_kitchen_demand_csv(token: str, from_date: Optional[str]=None, to_date: Optional[str]=None, store_id: Optional[int]=None):
    rpt = central_kitchen_demand(token, from_date, to_date, store_id)
    out = 'Date,Location,Store,SKU,Item,Category,Demand Quantity,Order Count,Gross Value\n'
    for r in rpt['detail']:
        out += f'{r.get("demand_date")},{r.get("location")},{r.get("store_name")},{r.get("sku")},{r.get("item_name")},{r.get("category")},{r.get("demand_qty")},{r.get("order_count")},{round(float(r.get("gross_value") or 0),2)}\n'
    return Response(out, media_type='text/csv', headers={'Content-Disposition':'attachment; filename=central_kitchen_demand.csv'})

@app.get('/api/admin/order-date-report')
def order_date_report(token: str, from_date: Optional[str]=None, to_date: Optional[str]=None):
    require_admin(token)
    from_date = from_date or (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    to_date = to_date or datetime.date.today().isoformat()
    with conn() as c:
        data = rows(c.execute("""select date(o.created_at) as order_date,
            count(distinct o.id) as total_orders,
            count(distinct case when o.payment_status='success' then o.id end) as paid_orders,
            count(distinct case when o.payment_status!='success' then o.id end) as unpaid_orders,
            count(distinct case when o.source='mobile' then o.id end) as mobile_orders,
            count(distinct case when o.source='kiosk' then o.id end) as kiosk_orders,
            count(distinct case when o.source='cashier' then o.id end) as cashier_orders,
            coalesce(sum(oi.quantity),0) as dishes,
            coalesce(sum(distinct o.subtotal),0) as subtotal,
            coalesce(sum(distinct o.tax_total),0) as tax_total,
            coalesce(sum(distinct o.total),0) as total_value
        from orders o
        left join order_items oi on oi.order_id=o.id
        where date(o.created_at) between date(?) and date(?)
        group by date(o.created_at)
        order by order_date desc""", (from_date, to_date)))
    grand = {
        'orders': sum(int(r.get('total_orders') or 0) for r in data),
        'paid_orders': sum(int(r.get('paid_orders') or 0) for r in data),
        'dishes': sum(int(r.get('dishes') or 0) for r in data),
        'subtotal': round(sum(float(r.get('subtotal') or 0) for r in data), 2),
        'tax_total': round(sum(float(r.get('tax_total') or 0) for r in data), 2),
        'total_value': round(sum(float(r.get('total_value') or 0) for r in data), 2)
    }
    return {'from_date': from_date, 'to_date': to_date, 'rows': data, 'grand': grand}

@app.get('/api/admin/order-date-report.csv')
def order_date_report_csv(token: str, from_date: Optional[str]=None, to_date: Optional[str]=None):
    rpt = order_date_report(token, from_date, to_date)
    out = 'Date,Total Orders,Paid Orders,Unpaid Orders,Mobile Orders,Kiosk Orders,Cashier Orders,Dishes,Subtotal,Tax Total,Total Value\n'
    for r in rpt['rows']:
        out += f'{r.get("order_date")},{r.get("total_orders")},{r.get("paid_orders")},{r.get("unpaid_orders")},{r.get("mobile_orders")},{r.get("kiosk_orders")},{r.get("cashier_orders")},{r.get("dishes")},{round(float(r.get("subtotal") or 0),2)},{round(float(r.get("tax_total") or 0),2)},{round(float(r.get("total_value") or 0),2)}\n'
    return Response(out, media_type='text/csv', headers={'Content-Disposition':'attachment; filename=order_date_report.csv'})

@app.get('/api/admin/users')
def admin_users(token: str):
    require_admin(token)
    with conn() as c: return {'users': rows(c.execute('select id,mobile,name,email,role,preferred_store_id,created_at from users order by id desc'))}

@app.get('/api/admin/orders')
def admin_orders(token: str):
    require_admin(token)
    with conn() as c:
        data=rows(c.execute('select o.*, s.name store_name from orders o join stores s on s.id=o.store_id order by o.id desc limit 100'))
    return {'orders':data}
