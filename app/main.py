import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

import sentry_sdk
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).parent


def init_sentry():
    dsn = os.environ.get("SENTRY_DSN")
    if not dsn:
        return False
    sentry_sdk.init(
        dsn=dsn,
        environment=os.environ.get("SENTRY_ENVIRONMENT", "production"),
        traces_sample_rate=0.0,
    )
    return True


def db_path():
    return os.environ.get("DATABASE_PATH", str(BASE_DIR.parent / "reviews.db"))


def connect():
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    return conn


SEED_PRODUCTS = [
    ("Trail Backpack", "Waterproof 30L pack for day hikes."),
    ("Ceramic Mug", "Dishwasher-safe 350ml mug."),
    ("Desk Lamp", "Dimmable LED lamp with USB charging."),
]

SEED_REVIEWS = [
    (1, 5, "Carried it all summer."),
    (1, 4, "Great, straps could be softer."),
    (2, 3, "Fine for the price."),
]


def init_db(seed=True):
    with connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS products ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '')"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS reviews ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER NOT NULL REFERENCES products(id), "
            "rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5), comment TEXT NOT NULL DEFAULT '')"
        )
        count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if seed and count == 0:
            conn.executemany("INSERT INTO products (name, description) VALUES (?, ?)", SEED_PRODUCTS)
            conn.executemany(
                "INSERT INTO reviews (product_id, rating, comment) VALUES (?, ?, ?)", SEED_REVIEWS
            )


def average_rating(ratings):
    if not ratings:
        return 0
    return round(sum(ratings) / len(ratings), 2)


@asynccontextmanager
async def lifespan(app):
    init_sentry()
    init_db(seed=os.environ.get("SEED_DEMO_DATA", "1") != "0")
    yield


app = FastAPI(title="Product Reviews", lifespan=lifespan)


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)


class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=1000)


def get_product_or_404(conn, product_id):
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return row


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/products")
def list_products():
    with connect() as conn:
        rows = conn.execute("SELECT id, name, description FROM products ORDER BY id").fetchall()
    return [dict(r) for r in rows]


@app.post("/products", status_code=201)
def create_product(product: ProductIn):
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO products (name, description) VALUES (?, ?)",
            (product.name, product.description),
        )
        product_id = cur.lastrowid
    return {"id": product_id, "name": product.name, "description": product.description}


@app.post("/products/{product_id}/reviews", status_code=201)
def add_review(product_id: int, review: ReviewIn):
    with connect() as conn:
        get_product_or_404(conn, product_id)
        cur = conn.execute(
            "INSERT INTO reviews (product_id, rating, comment) VALUES (?, ?, ?)",
            (product_id, review.rating, review.comment),
        )
        review_id = cur.lastrowid
    return {"id": review_id, "product_id": product_id, "rating": review.rating, "comment": review.comment}


@app.get("/products/{product_id}/reviews")
def list_reviews(product_id: int):
    with connect() as conn:
        get_product_or_404(conn, product_id)
        rows = conn.execute(
            "SELECT id, rating, comment FROM reviews WHERE product_id = ? ORDER BY id DESC",
            (product_id,),
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/products/{product_id}/rating")
def product_rating(product_id: int):
    with connect() as conn:
        product = get_product_or_404(conn, product_id)
        ratings = [
            r["rating"]
            for r in conn.execute("SELECT rating FROM reviews WHERE product_id = ?", (product_id,))
        ]
    return {
        "product_id": product["id"],
        "average_rating": average_rating(ratings),
        "review_count": len(ratings),
    }
