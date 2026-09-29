"""Small catalog and order manager with server-side price and stock checks."""
from datetime import datetime, timezone
import re

PRODUCTS = [
    ("audit-kit", "Website audit kit", "Operations", 4900, 14, "Checklist, scorecard, and report template for a service website review."),
    ("crm-starter", "CRM starter pack", "Business", 3900, 18, "Lead import template, pipeline sheet, and follow-up scripts for small teams."),
    ("store-copy", "Product page copy pack", "Ecommerce", 2900, 25, "Short-form ecommerce copy blocks for descriptions, FAQs, and guarantees."),
    ("qa-plan", "QA launch plan", "Testing", 3500, 20, "Manual QA checklist, browser matrix, and release sign-off worksheet."),
]

STATUSES = {"Paid", "Packed", "Sent", "Refunded"}


def init(db):
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS products(
            sku TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price_cents INTEGER NOT NULL CHECK(price_cents >= 0),
            stock INTEGER NOT NULL CHECK(stock >= 0),
            description TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY,
            customer TEXT NOT NULL,
            email TEXT NOT NULL,
            total_cents INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Paid',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS order_items(
            order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            sku TEXT NOT NULL REFERENCES products(sku),
            quantity INTEGER NOT NULL CHECK(quantity > 0),
            unit_cents INTEGER NOT NULL,
            PRIMARY KEY(order_id, sku)
        );
        """
    )
    for product in PRODUCTS:
        db.execute(
            """INSERT OR IGNORE INTO products(sku,name,category,price_cents,stock,description)
               VALUES(?,?,?,?,?,?)""",
            product,
        )


def rows(db, query, params=()):
    return [dict(row) for row in db.execute(query, params)]


def order_summary(db):
    return rows(
        db,
        """
        SELECT o.*, COALESCE(SUM(i.quantity), 0) AS item_count
        FROM orders o
        LEFT JOIN order_items i ON i.order_id = o.id
        GROUP BY o.id
        ORDER BY o.id DESC
        """,
    )


def normalize_cart(data):
    raw = data.get("items")
    if not isinstance(raw, list) or not raw:
        raise ValueError("Add at least one product to the cart.")
    cart = {}
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("Each cart item must be an object.")
        sku = str(item.get("sku", "")).strip()
        quantity = item.get("quantity")
        if not isinstance(quantity, int) or quantity < 1 or quantity > 20:
            raise ValueError("Cart quantities must be whole numbers from 1 to 20.")
        cart[sku] = cart.get(sku, 0) + quantity
    return cart


def handle(method, path, data, db):
    if method == "GET" and path == "/api/state":
        return {
            "products": rows(db, "SELECT * FROM products ORDER BY category, name"),
            "orders": order_summary(db),
        }

    if method == "POST" and path == "/api/orders":
        customer = str(data.get("customer", "")).strip()
        email = str(data.get("email", "")).strip().lower()
        if not 2 <= len(customer) <= 80 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            raise ValueError("Enter a customer name and valid email.")
        cart = normalize_cart(data)
        placeholders = ",".join("?" for _ in cart)
        products = {
            row["sku"]: dict(row)
            for row in db.execute(f"SELECT * FROM products WHERE sku IN ({placeholders})", tuple(cart))
        }
        if set(products) != set(cart):
            raise ValueError("Cart contains an unknown product.")
        for sku, quantity in cart.items():
            if products[sku]["stock"] < quantity:
                raise ValueError(f"{products[sku]['name']} does not have enough stock.")
        total = sum(products[sku]["price_cents"] * quantity for sku, quantity in cart.items())
        order = db.execute(
            "INSERT INTO orders(customer,email,total_cents,created_at) VALUES(?,?,?,?)",
            (customer, email, total, datetime.now(timezone.utc).isoformat()),
        )
        for sku, quantity in cart.items():
            db.execute("UPDATE products SET stock = stock - ? WHERE sku = ?", (quantity, sku))
            db.execute(
                "INSERT INTO order_items(order_id,sku,quantity,unit_cents) VALUES(?,?,?,?)",
                (order.lastrowid, sku, quantity, products[sku]["price_cents"]),
            )
        return {"id": order.lastrowid, "total_cents": total}

    if method == "POST" and path == "/api/status":
        status = str(data.get("status", "")).strip()
        if status not in STATUSES:
            raise ValueError("Choose a listed order status.")
        row = db.execute("UPDATE orders SET status=? WHERE id=?", (status, data.get("id")))
        if not row.rowcount:
            raise LookupError()
        return {"ok": True}

    raise LookupError()
