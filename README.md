# Truflux FoodFlow v1.1.16 — Login-Enforced Landing + Mobile Menu Pagination Build

This build is optimized for Windows demo use and runs only on the Python/FastAPI server at port 8000. It does not require Node, npm, Vite, or port 5173.

## What is included

- Landing page with mode selection: Mobile App, Cashier POS, Kiosk, Admin
- Landing page enforces login for each selected app mode for a complete demo flow
- Mobile number + OTP login with six digit boxes
- Persistent session after login until logout
- Consumer app shows only Menu, Cart, Orders, Profile
- Square menu tiles; tap the dish tile to add to cart
- No separate Add button on consumer menu tiles
- Larger touch-friendly buttons
- Menu lazy loading / pagination: initial visible items only, more load as the user scrolls
- Orders page shows minimal order cards
- Tapping an order opens full order details, QR and receipt
- Profile icon shows uploaded user display photo
- Full receipt download retained
- Kiosk and cashier receipt printing retained
- Admin test data button retained
- Consolidated order report by date retained

## Windows quick start

1. Extract the ZIP to:

```text
C:\1food
```

2. Double-click:

```text
start_app_windows.bat
```

3. Open:

```text
http://localhost:8000/
```

## Direct URLs

```text
Landing:  http://localhost:8000/
Mobile:   http://localhost:8000/app
Cashier:  http://localhost:8000/cashier
Kiosk:    http://localhost:8000/kiosk
Admin:    http://localhost:8000/admin
Health:   http://localhost:8000/api/health
```

## Demo login

```text
Mobile: 9999999999
OTP:    123456
```

From the landing page, each option clears the previous demo session and opens the selected mode login. After logging into that mode, the session remains active until Logout.

## Important

Use only port 8000. Do not use `http://localhost:5173`; this build does not use Vite/npm.


## v1.1.16 updates
- After mobile payment, the app opens a dedicated Receipt page immediately.
- Orders tab now remains historical order list only; tap any card to open details.
- Consumer menu tiles are smaller, perfect square tiles.
- Menu tile tap is optimized and no longer re-renders the full menu on every tap.
- Proper scannable QR PNG generated for the order number.
- Menu infinite loading loads visible batches and adds more while scrolling.


## v1.1.16 Central Kitchen Demand Planning

Added Admin > Central Kitchen Demand report for central kitchen production planning. It shows confirmed paid demand by date, store/location, SKU, menu item, category, demand quantity, order count and gross item value. It includes date range filtering, location filtering, CSV export, location summary, item summary and an AI suggested cooking plan with a prototype 10% buffer.


## v1.1.16 update
- Fixed Kiosk menu visibility issue.
- Kiosk now renders menu items inside a proper square tile grid.
- Added empty-state message if a store has no menu items.
- Kiosk cart button remains easy to access at the bottom.


## v1.1.16 Delivery / Pickup Fulfilment Update

Added a dedicated Delivery / Pickup page:

- URL: `http://localhost:8000/delivery`
- Staff logs in using mobile + OTP.
- Customer presents the QR receipt from mobile/kiosk/cashier.
- Staff scans or enters the order number / QR token.
- System validates payment, displays order summary, and marks the order as `fulfilled`.
- Already fulfilled orders cannot be fulfilled again.

Landing page now includes: Mobile App, Cashier POS, Kiosk, Delivery / Pickup, and Admin Configuration.

## Railway Port Fix — v1.1.17

This build uses `python -m app.serve` for Railway startup. The server reads Railway's dynamic `PORT` environment variable inside Python and converts it to an integer before starting Uvicorn.

Use this Railway start command:

```bash
python -m app.serve
```

Do not use:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Some Railway/Docker configurations pass `$PORT` literally instead of expanding it, which causes the error: `$PORT is not a valid integer`.
