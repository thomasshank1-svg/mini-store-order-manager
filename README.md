# Form & Function

Form & Function is a mini ecommerce and order-management demo. It has a digital product catalog, browser cart, simulated checkout, stock reduction, and order status updates.

## Run

```sh
python3 server.py
```

Open `http://127.0.0.1:8103`.

## What it demonstrates

- Catalog and order API design
- Server-side price calculation
- Inventory checks and stock reduction
- SQLite order and item tables
- Status management for small operations teams

## Test

```sh
python3 -m unittest discover -s tests -v
```

Checkout is simulated and never charges a card.
