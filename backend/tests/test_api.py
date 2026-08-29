import io
import json
import numpy as np
import cv2
from io import BytesIO


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_valid_image(client, sample_image_bytes):
    response = client.post(
        "/api/analyze",
        files={"file": ("test.png", sample_image_bytes, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["filename"] == "test.png"
    assert 0 <= data["quality_score"] <= 100
    assert data["quality_label"] in ["ACCEPTABLE", "DEGRADED", "POTENTIALLY_DEFECTIVE"]
    assert isinstance(data["issues"], list)
    assert "statistics" in data
    assert "model" in data
    assert data["model"]["name"] == "RandomForestClassifier"
    assert "created_at" in data


def test_analyze_blur_image(client, blur_image_bytes):
    response = client.post(
        "/api/analyze",
        files={"file": ("blurry.png", blur_image_bytes, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["quality_score"] <= 100


def test_analyze_invalid_file_type(client):
    response = client.post(
        "/api/analyze",
        files={"file": ("test.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400


def test_analyze_empty_file(client):
    response = client.post(
        "/api/analyze",
        files={"file": ("empty.png", b"", "image/png")},
    )
    assert response.status_code == 400


def test_analyze_corrupt_image(client):
    response = client.post(
        "/api/analyze",
        files={"file": ("corrupt.png", b"not an image", "image/png")},
    )
    assert response.status_code == 400


def test_analyze_oversized_file(client):
    large_data = b"x" * (11 * 1024 * 1024)
    response = client.post(
        "/api/analyze",
        files={"file": ("large.png", large_data, "image/png")},
    )
    assert response.status_code == 413


def test_list_analyses_empty(client):
    response = client.get("/api/analyses")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_analyses_with_data(client, sample_image_bytes):
    client.post(
        "/api/analyze",
        files={"file": ("test1.png", sample_image_bytes, "image/png")},
    )
    response = client.get("/api/analyses")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1


def test_list_analyses_pagination(client, sample_image_bytes):
    for i in range(3):
        client.post(
            "/api/analyze",
            files={"file": (f"test_{i}.png", sample_image_bytes, "image/png")},
        )
    response = client.get("/api/analyses?page=1&page_size=2")
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["total_pages"] == 2


def test_list_analyses_search(client, sample_image_bytes):
    client.post(
        "/api/analyze",
        files={"file": ("unique_name.png", sample_image_bytes, "image/png")},
    )
    response = client.get("/api/analyses?search=unique_name")
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["filename"] == "unique_name.png"


def test_list_analyses_filter_label(client, sample_image_bytes):
    client.post(
        "/api/analyze",
        files={"file": ("test.png", sample_image_bytes, "image/png")},
    )
    response = client.get("/api/analyses?label=ACCEPTABLE")
    assert response.status_code == 200


def test_get_analysis_detail(client, sample_image_bytes):
    res = client.post(
        "/api/analyze",
        files={"file": ("test.png", sample_image_bytes, "image/png")},
    )
    analysis_id = res.json()["id"]

    response = client.get(f"/api/analyses/{analysis_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == analysis_id
    assert "statistics" in data
    assert "issues" in data


def test_get_analysis_not_found(client):
    response = client.get("/api/analyses/99999")
    assert response.status_code == 404


def test_delete_analysis(client, sample_image_bytes):
    res = client.post(
        "/api/analyze",
        files={"file": ("test.png", sample_image_bytes, "image/png")},
    )
    analysis_id = res.json()["id"]

    response = client.delete(f"/api/analyses/{analysis_id}")
    assert response.status_code == 200

    response = client.get(f"/api/analyses/{analysis_id}")
    assert response.status_code == 404


def test_delete_analysis_not_found(client):
    response = client.delete("/api/analyses/99999")
    assert response.status_code == 404


def test_statistics_empty(client):
    response = client.get("/api/statistics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_analyses"] == 0
    assert data["average_score"] == 0.0


def test_statistics_with_data(client, sample_image_bytes):
    client.post(
        "/api/analyze",
        files={"file": ("test.png", sample_image_bytes, "image/png")},
    )
    response = client.get("/api/statistics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_analyses"] == 1
    assert data["average_score"] > 0
