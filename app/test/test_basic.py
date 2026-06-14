import requests
import pytest

BASE_URL = "http://localhost:9000"

@pytest.mark.parametrize(
    "name,payload,expected_status",
    [
        (
            "ok",
            {
                "user_id": "test",
                "test": "test",
            },
            202,
        )
    ],
)
def test(name, payload, expected_status):
    url = f"{BASE_URL}/items/~test"
    resp = requests.post(url, json=payload, timeout=10)

    if expected_status == 202:
        body = resp.json()
        assert resp.status_code == 202
        assert "operation_id" in body
        assert body.get("error_code") == "A001"

    elif expected_status == 500:
        body = resp.json()
        assert resp.status_code == 500
        assert "error_code" in body
