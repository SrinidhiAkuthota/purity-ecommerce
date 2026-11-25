#!/usr/bin/env python3
"""
Purity — lightweight Flask backend.

Serves the existing static frontend (index.html, objects.html, etc.) AND
a small JSON API backing it:

    GET  /api/products            -> catalog (filter by ?category=, ?q=)
    GET  /api/products/<id>       -> single product
    GET  /api/search?q=...        -> sitewide product search (name/desc/category)
    POST /api/contact             -> store a contact form submission
    POST /api/newsletter          -> store a newsletter signup
    POST /api/orders              -> log a "checkout" (cart contents)
    GET  /api/orders/<id>         -> look up an order confirmation
    GET  /api/health              -> health check (handy for Render)

Storage: a single SQLite file (purity.db), created automatically on first run.
No external services, no ORM — just the standard library + Flask, so it's
cheap to run on Render's free tier.
"""
import os
import re
import json
import sqlite3
from datetime import datetime, timezone

from flask import Flask, jsonify, request, send_from_directory, g

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "purity.db")

app = Flask(__name__, static_folder=BASE_DIR, static_url_path="")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS products (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            category    TEXT NOT NULL,
            price       INTEGER,
            old_price   INTEGER,
            description TEXT,
            emoji       TEXT,
            badge       TEXT,
            page        TEXT NOT NULL,
            rating      REAL DEFAULT 5,
            in_stock    INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS contact_messages (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name   TEXT,
            last_name    TEXT,
            email        TEXT NOT NULL,
            order_number TEXT,
            topic        TEXT,
            message      TEXT NOT NULL,
            created_at   TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS newsletter_signups (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            email      TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS orders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            items_json  TEXT NOT NULL,
            subtotal    INTEGER NOT NULL,
            delivery_fee INTEGER DEFAULT 0,
            total_amount INTEGER DEFAULT 0,
            customer_name TEXT,
            email       TEXT,
            phone       TEXT,
            address     TEXT,
            payment_method TEXT,
            payment_status TEXT DEFAULT 'demo',
            created_at  TEXT NOT NULL
        );
        """
    )
    # Backward-compatible migration for an existing local database.
    existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(orders)")}
    for column, definition in [
        ("delivery_fee", "INTEGER DEFAULT 0"), ("total_amount", "INTEGER DEFAULT 0"),
        ("customer_name", "TEXT"), ("email", "TEXT"), ("phone", "TEXT"),
        ("address", "TEXT"), ("payment_method", "TEXT"),
        ("payment_status", "TEXT DEFAULT 'demo'"),
    ]:
        if column not in existing_columns:
            conn.execute(f"ALTER TABLE orders ADD COLUMN {column} {definition}")
    conn.commit()
    conn.close()


# Seed data mirrors the products already hardcoded across the static pages.
# (name, category, price, old_price, description, emoji, badge, page, rating, in_stock)
SEED_PRODUCTS = [
    ("Hiba Candle", "Living", 950, None,
     "Hand-poured beeswax with bergamot & cedarwood. Burns 60+ hrs.",
     "🕯️", "New", "objects.html", 5.0, 1),
    ("Ceramic Pour-Over", "Kitchen", 2200, 2800,
     "Single-origin ritual, every morning. Matte white glaze.",
     "☕", "Sale", "objects.html", 5.0, 1),
    ("Linen Journal", "Stationery", 780, None,
     "Stone-washed linen cover, 200 pages of acid-free paper.",
     "📓", None, "objects.html", 4.0, 1),
    ("Hinoki Soap", "Wellness", 520, None,
     "Japanese cypress & clay. Cold-pressed, no synthetics.",
     "🧼", "Bestseller", "objects.html", 5.0, 1),
    ("Teak Coaster Set", "Living", 680, 900,
     "Solid teak, naturally water-resistant. Set of four.",
     "🪵", "Sale", "objects.html", 4.0, 1),
    ("Brass Bookmark", "Stationery", 390, None,
     "Solid brushed brass. Engraved with a single meridian line.",
     "🔖", None, "objects.html", 4.0, 1),
    ("Ritual Face Oil", "Wellness", 1650, None,
     "Seven-seed blend with rosehip & sea buckthorn.",
     "🌸", "New", "objects.html", 5.0, 1),
    ("Clay Salad Bowl", "Kitchen", 1800, 2200,
     "Wheel-thrown stoneware. Each piece uniquely imperfect.",
     "🥗", "Sale", "objects.html", 5.0, 1),
    ("Arch Mirror — Small", "Mirrors", 3800, None,
     "Solid teak frame, hand-finished. 50 × 30cm arc form.",
     "🪞", "New", "living.html", 4.0, 1),
    ("Stoneware Vase", "Vessels", 1950, None,
     "Narrow-neck form in warm grey. 28cm tall.",
     "🌱", None, "living.html", 5.0, 1),
    ("Hiba Candle — Oud Edition", "Living", 1150, None,
     "Our signature beeswax candle now in a deep oud & amber accord. Limited run of 200.",
     "🕯️", "New", "new-in.html", 5.0, 1),
    ("Cold Cream No. 4", "Wellness", 980, None,
     "Whipped shea and calendula. No fragrance, no compromise.",
     "🌿", "New", "new-in.html", 5.0, 1),
    ("The Terra Collection", "Preview", None, None,
     "Hand-thrown terracotta vessels and planters. Glazed in a single matte finish. Dropping May 12.",
     "🪴", "Preview", "new-in.html", None, 0),
    ("Ash Teapot", "Kitchen", 2400, None,
     "Wheel-thrown in grey stoneware. Holds exactly two cups — by design.",
     "🫖", "New", "new-in.html", 5.0, 1),
    ("Mineral Toner", "Wellness", 840, None,
     "Rose water & zinc. Balances, never strips. pH 5.5.",
     "🧴", "New", "new-in.html", 5.0, 1),
    ("Graphite Pencil Set", "Stationery", 460, None,
     "Six Japanese pencils, 2H–6B. Wrapped in washi paper.",
     "✏️", "New", "new-in.html", 4.0, 1),
]


def seed_db():
    conn = sqlite3.connect(DB_PATH)
    count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if count == 0:
        conn.executemany(
            """INSERT INTO products
               (name, category, price, old_price, description, emoji, badge, page, rating, in_stock)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            SEED_PRODUCTS,
        )
        conn.commit()
    conn.close()


def row_to_product(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "price": row["price"],
        "old_price": row["old_price"],
        "description": row["description"],
        "emoji": row["emoji"],
        "badge": row["badge"],
        "page": row["page"],
        "rating": row["rating"],
        "in_stock": bool(row["in_stock"]),
    }


# ---------------------------------------------------------------------------
# Static frontend
# ---------------------------------------------------------------------------
@app.route("/")
def serve_index():
    return send_from_directory(BASE_DIR, "index.html")


# ---------------------------------------------------------------------------
# Product catalog + search
# ---------------------------------------------------------------------------
@app.route("/api/products")
def list_products():
    category = request.args.get("category", "").strip()
    q = request.args.get("q", "").strip()

    sql = "SELECT * FROM products WHERE 1=1"
    params = []
    if category and category.lower() not in ("all", ""):
        sql += " AND LOWER(category) = LOWER(?)"
        params.append(category)
    if q:
        sql += " AND (LOWER(name) LIKE ? OR LOWER(description) LIKE ? OR LOWER(category) LIKE ?)"
        like = f"%{q.lower()}%"
        params.extend([like, like, like])
    sql += " ORDER BY id"

    rows = get_db().execute(sql, params).fetchall()
    return jsonify({"products": [row_to_product(r) for r in rows], "count": len(rows)})


@app.route("/api/products/<int:product_id>")
def get_product(product_id):
    row = get_db().execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(row_to_product(row))


@app.route("/api/search")
def search_products():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"products": [], "count": 0})

    like = f"%{q.lower()}%"
    rows = get_db().execute(
        """SELECT * FROM products
           WHERE LOWER(name) LIKE ? OR LOWER(description) LIKE ? OR LOWER(category) LIKE ?
           ORDER BY in_stock DESC, id
           LIMIT 12""",
        (like, like, like),
    ).fetchall()
    return jsonify({"products": [row_to_product(r) for r in rows], "count": len(rows)})


# ---------------------------------------------------------------------------
# Contact form
# ---------------------------------------------------------------------------
@app.route("/api/contact", methods=["POST"])
def submit_contact():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    message = (data.get("message") or "").strip()

    if not email or not EMAIL_RE.match(email):
        return jsonify({"error": "A valid email address is required."}), 400
    if not message:
        return jsonify({"error": "Message can't be empty."}), 400

    conn = get_db()
    conn.execute(
        """INSERT INTO contact_messages
           (first_name, last_name, email, order_number, topic, message, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (
            (data.get("firstName") or "").strip(),
            (data.get("lastName") or "").strip(),
            email,
            (data.get("orderNumber") or "").strip(),
            (data.get("topic") or "").strip(),
            message,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    return jsonify({"status": "ok", "message": "Message received — we'll reply within 1 business day."}), 201


# ---------------------------------------------------------------------------
# Newsletter
# ---------------------------------------------------------------------------
@app.route("/api/newsletter", methods=["POST"])
def submit_newsletter():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()

    if not email or not EMAIL_RE.match(email):
        return jsonify({"error": "A valid email address is required."}), 400

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO newsletter_signups (email, created_at) VALUES (?, ?)",
            (email, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        return jsonify({"status": "ok", "message": "You're on the list."}), 201
    except sqlite3.IntegrityError:
        return jsonify({"status": "ok", "message": "You're already subscribed."}), 200


# ---------------------------------------------------------------------------
# Orders (checkout logging)
# ---------------------------------------------------------------------------
@app.route("/api/orders", methods=["POST"])
def create_order():
    """Create a portfolio/demo order. No real payment is processed."""
    data = request.get_json(silent=True) or {}
    items = data.get("items") or []
    customer_name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    address = (data.get("address") or "").strip()
    payment_method = (data.get("payment_method") or "").strip().lower()
    allowed_methods = {"upi", "card", "wallet", "cod"}

    if not isinstance(items, list) or not items:
        return jsonify({"error": "Your cart is empty."}), 400
    if not customer_name or len(customer_name) > 100:
        return jsonify({"error": "Please enter your name."}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"error": "Please enter a valid email address."}), 400
    if not phone or len(phone) < 8 or len(phone) > 20:
        return jsonify({"error": "Please enter a valid phone number."}), 400
    if not address or len(address) < 8 or len(address) > 500:
        return jsonify({"error": "Please enter a complete delivery address."}), 400
    if payment_method not in allowed_methods:
        return jsonify({"error": "Please choose a payment method."}), 400

    conn = get_db()
    subtotal = 0
    clean_items = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = (item.get("name") or "").strip()
        try:
            qty = int(item.get("qty") or 0)
        except (TypeError, ValueError):
            qty = 0
        if not name or qty < 1 or qty > 20:
            return jsonify({"error": "One or more cart quantities are invalid."}), 400
        row = conn.execute(
            "SELECT name, price FROM products WHERE LOWER(name) = LOWER(?) AND in_stock = 1",
            (name,),
        ).fetchone()
        if row is None or row["price"] is None:
            return jsonify({"error": f'"{name}" is unavailable. Please refresh your cart.'}), 400
        price = int(row["price"])
        clean_items.append({"name": row["name"], "price": price, "qty": qty})
        subtotal += price * qty

    if not clean_items:
        return jsonify({"error": "Your cart does not contain purchasable products."}), 400

    delivery_fee = 0 if subtotal >= 2500 else 99
    total_amount = subtotal + delivery_fee
    created_at = datetime.now(timezone.utc).isoformat()
    payment_status = "pay-on-delivery" if payment_method == "cod" else "demo-payment"
    cur = conn.execute(
        """INSERT INTO orders
           (items_json, subtotal, delivery_fee, total_amount, customer_name, email, phone, address,
            payment_method, payment_status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (json.dumps(clean_items), subtotal, delivery_fee, total_amount, customer_name, email, phone,
         address, payment_method, payment_status, created_at),
    )
    conn.commit()
    return jsonify({
        "status": "ok", "order_id": cur.lastrowid, "subtotal": subtotal,
        "delivery_fee": delivery_fee, "total_amount": total_amount,
        "items": clean_items, "payment_method": payment_method,
        "payment_status": payment_status,
        "message": "Demo order placed successfully. No online payment was charged.",
        "created_at": created_at,
    }), 201


@app.route("/api/orders/<int:order_id>")
def get_order(order_id):
    row = get_db().execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Order not found"}), 404
    return jsonify({
        "order_id": row["id"],
        "items": json.loads(row["items_json"]),
        "subtotal": row["subtotal"],
        "delivery_fee": row["delivery_fee"],
        "total_amount": row["total_amount"],
        "customer_name": row["customer_name"],
        "email": row["email"],
        "payment_method": row["payment_method"],
        "payment_status": row["payment_status"],
        "created_at": row["created_at"],
    })


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Init on import (so `gunicorn app:app` on Render also seeds the DB)
# ---------------------------------------------------------------------------
init_db()
seed_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
