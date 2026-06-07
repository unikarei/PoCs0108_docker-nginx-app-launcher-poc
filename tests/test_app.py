from fastapi.testclient import TestClient         # Import synchronous API test client.

from app.main import app, add_numbers             # Import app and pure helper function.


# Test setup block: create one reusable client for all test cases.
client = TestClient(app)                          # Bind test client to FastAPI app.


# Test block: verify home page status, type, and expected content snippets.
def test_home_page_returns_expected_content() -> None:
    response = client.get("/")                    # Request the root HTML page.

    assert response.status_code == 200            # Confirm successful HTTP response.
    assert "text/html" in response.headers["content-type"]  # Confirm HTML media type.
    assert "Test Function POC" in response.text  # Confirm page title text.
    assert "This is a local Docker and Nginx POC application." in response.text  # Body text.
    assert "./api/health" in response.text       # Confirm health link exists.
    assert "./api/add?a=1&amp;b=2" in response.text  # Confirm add link exists.


# Test block: verify stable payload from health endpoint.
def test_health_endpoint_returns_expected_json() -> None:
    response = client.get("/api/health")          # Request health endpoint.

    assert response.status_code == 200            # Confirm successful HTTP response.
    assert response.json() == {"status": "ok", "app": "test-function-poc"}  # Contract.


# Test block: verify sum endpoint computes expected result.
def test_add_endpoint_returns_sum() -> None:
    response = client.get("/api/add?a=1&b=2")    # Request addition endpoint.

    assert response.status_code == 200            # Confirm successful HTTP response.
    assert response.json() == {"a": 1, "b": 2, "result": 3}  # Validate numeric payload.


# Test block: verify helper normalization behavior for whole-number floats.
def test_add_numbers_normalizes_whole_numbers() -> None:
    assert add_numbers(1.0, 2.5) == {"a": 1, "b": 2.5, "result": 3.5}  # 1.0 -> 1.
