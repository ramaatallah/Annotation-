"""Integration tests for Annotations CRUD and Search API."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_system_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_create_and_retrieve_annotation():
    payload = {
        "url": "https://najah.edu/ar/about",
        "page_title": "عن جامعة النجاح",
        "selected_text": "جامعة النجاح الوطنية تقع في مدينة نابلس",
        "note": "ملاحظة أولى حول الجامعة والموقع الجغرافي",
        "color": "#FFE082",
        "auto_analyze": True,
    }

    # 1. Create annotation
    post_res = client.post("/v1/annotations", json=payload)
    assert post_res.status_code == 201
    created = post_res.json()
    assert created["id"] is not None
    assert created["selected_text"] == payload["selected_text"]
    assert created["note"] == payload["note"]
    assert len(created["entities"]) > 0

    ann_id = created["id"]

    # 2. Get annotation by ID
    get_res = client.get(f"/v1/annotations/{ann_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["id"] == ann_id

    # Check entities and roots attached
    entities = data["entities"]
    entity_texts = [e["text"] for e in entities]
    assert any("جامعة النجاح" in t for t in entity_texts)

    # 3. List by URL
    list_res = client.get("/v1/annotations", params={"url": payload["url"]})
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # 4. Update note
    update_res = client.put(
        f"/v1/annotations/{ann_id}",
        json={"note": "ملاحظة معدلة ومحدثة بنجاح"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["note"] == "ملاحظة معدلة ومحدثة بنجاح"

    # 5. Search by category
    search_res = client.get("/v1/search", params={"category": "UNIVERSITY"})
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total_count"] >= 1

    # 6. Delete annotation
    del_res = client.delete(f"/v1/annotations/{ann_id}")
    assert del_res.status_code == 200

    # Verify deletion
    verify_res = client.get(f"/v1/annotations/{ann_id}")
    assert verify_res.status_code == 404
