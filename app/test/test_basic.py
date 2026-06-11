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
                "affiliation": "test",
            },
            200,
        )
    ],
)
def test(name, payload, expected_status):
    url = f"{BASE_URL}/items/~test"
    resp = requests.post(url, data=payload, timeout=10)

    if expected_status == 200:
        body = resp.json()
        assert "operation_id" in body.get('detail')
        assert "result" in body.get('detail')
        assert "spending_time(s)" in body.get('detail')
        

    elif expected_status == 500:
        body = resp.json()
        assert "detail" in body.get('detail')
