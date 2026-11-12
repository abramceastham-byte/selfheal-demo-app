import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    monkeypatch.setenv("SEED_DEMO_DATA", "0")
    with TestClient(main.app) as c:
        yield c


def make_product(client, name="Widget"):
    return client.post("/products", json={"name": name, "description": "A widget"}).json()


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_index_page(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Product Reviews" in res.text


def test_create_and_list_products(client):
    created = make_product(client, "Lamp")
    assert created["name"] == "Lamp"
    products = client.get("/products").json()
    assert [p["name"] for p in products] == ["Lamp"]


def test_create_product_requires_name(client):
    assert client.post("/products", json={"name": ""}).status_code == 422


def test_add_review_and_list(client):
    pid = make_product(client)["id"]
    res = client.post(f"/products/{pid}/reviews", json={"rating": 4, "comment": "Nice"})
    assert res.status_code == 201
    reviews = client.get(f"/products/{pid}/reviews").json()
    assert len(reviews) == 1
    assert reviews[0]["rating"] == 4


@pytest.mark.parametrize("rating", [0, 6, -1])
def test_rating_out_of_range_rejected(client, rating):
    pid = make_product(client)["id"]
    assert client.post(f"/products/{pid}/reviews", json={"rating": rating}).status_code == 422


def test_review_unknown_product_404(client):
    assert client.post("/products/999/reviews", json={"rating": 3}).status_code == 404


def test_average_rating_single_review(client):
    pid = make_product(client)["id"]
    client.post(f"/products/{pid}/reviews", json={"rating": 5})
    data = client.get(f"/products/{pid}/rating").json()
    assert data["average_rating"] == 5
    assert data["review_count"] == 1


def test_average_rating_multiple_reviews(client):
    pid = make_product(client)["id"]
    for rating in (5, 4, 4):
        client.post(f"/products/{pid}/reviews", json={"rating": rating})
    data = client.get(f"/products/{pid}/rating").json()
    assert data["average_rating"] == 4.33
    assert data["review_count"] == 3


def test_rating_unknown_product_404(client):
    assert client.get("/products/999/rating").status_code == 404


def test_sentry_disabled_without_dsn(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    assert main.init_sentry() is False


def test_average_rating_no_reviews(client):
    pid = make_product(client)["id"]
    res = client.get(f"/products/{pid}/rating")
    assert res.status_code == 200
    data = res.json()
    assert data["average_rating"] == 0
    assert data["review_count"] == 0

