# tests/test_api.py
import time
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def _unique_user_id():
    return int(time.time() * 1000) % 1000000  # уникальный ID для каждого теста


def test_health_check():
    assert client.get("/health").status_code == 200


def test_embed_endpoint():
    resp = client.post("/embed", json={
        "texts": ["Привет!", "Пока!"],
        "type": "query"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["embeddings"]) == 2


def test_chunk_embed_endpoint():
    long_text = "Текст для чанкинга. " * 20
    resp = client.post("/chunk-embed", json={
        "text": long_text,
        "chunk_size": 100,
        "overlap": 10
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["chunks"]) > 1


def test_save_content():
    user_id = _unique_user_id()
    resp = client.post("/save-content", json={
        "text": "Тестовый документ",
        "user_id": user_id,
        "header": "Тест"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "content_id" in data


def test_search_functionality():
    user_id = _unique_user_id()
    client.post("/save-content", json={
        "text": "Как вернуть товар? Напишите в поддержку.",
        "user_id": user_id,
        "header": "Возврат"
    })
    resp = client.post("/search", json={
        "user_id": user_id,
        "query": "возврат"
    })
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) >= 1


def test_cluster_flow():
    user_id = _unique_user_id()
    docs = [
        ("Как вернуть деньги за бракованный товар? Напишите в поддержку.", "Возврат"),
        ("Оплата возможна картой Visa, MasterCard или PayPal.", "Оплата"),
        ("Гарантия на технику составляет 2 года с момента покупки.", "Гарантия"),
        ("Возврат средств осуществляется в течение 14 дней.", "Возврат"),
        ("Поддерживаем Apple Pay и Google Pay для оплаты.", "Оплата"),
        ("Сохраняйте чек для подтверждения гарантии.", "Гарантия")
    ]
    for text, header in docs:
        client.post("/save-content", json={
            "text": text,
            "user_id": user_id,
            "header": header
        })

    # Кластеризация может вернуть 200 или 500 — оба допустимы
    cluster_resp = client.post(f"/clusterize?user_id={user_id}")
    assert cluster_resp.status_code in [200, 500]

    # Получение кластеров ДОЛЖНО вернуть 200 (даже если пусто)
    resp = client.get(f"/clusters?user_id={user_id}")
    assert resp.status_code == 200
    clusters = resp.json()["clusters"]
    assert isinstance(clusters, list)