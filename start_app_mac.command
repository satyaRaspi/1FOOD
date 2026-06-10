#!/bin/bash
cd "$(dirname "$0")"
echo "Starting Truflux FoodFlow v1.1.6"
echo "Landing:  http://localhost:8000/"
echo "App:      http://localhost:8000/app"
echo "Cashier:  http://localhost:8000/cashier"
echo "Kiosk:    http://localhost:8000/kiosk"
echo "Admin:    http://localhost:8000/admin"
python3 -m pip install -r requirements.txt
(sleep 2; open http://localhost:8000/) &
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
