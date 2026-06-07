from fastapi import FastAPI, Query               # Import FastAPI core and query validator.
from fastapi.responses import HTMLResponse       # Import explicit HTML response type.


# App setup block: create the FastAPI application object once at module load.
app = FastAPI(title="Test Function POC")        # Set a readable title for API docs.


# HTML template block: static page served by the root endpoint.
HOME_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Test Function POC</title>
  </head>
  <body>
    <main>
      <h1>Test Function POC</h1>
      <p>This is a local Docker and Nginx POC application.</p>
      <ul>
        <li><a href="./api/health">./api/health</a></li>
        <li><a href="./api/add?a=1&amp;b=2">./api/add?a=1&amp;b=2</a></li>
      </ul>
    </main>
  </body>
</html>
"""


# Utility block: normalize numbers for cleaner JSON output.
def normalize_number(value: float) -> int | float:
  """Return an int when the float has no fractional part."""
  if value.is_integer():                      # Check whether the value is mathematically whole.
    return int(value)                       # Convert to int for friendlier API output.
  return value                                # Keep float when fractional digits are present.


# Domain helper block: centralize addition logic used by the endpoint and tests.
def add_numbers(a: float, b: float) -> dict[str, int | float]:
  """Add two numbers and normalize each output field for readability."""
  result = a + b                              # Compute the raw sum.
  return {
    "a": normalize_number(a),             # Normalize input a for clean JSON shape.
    "b": normalize_number(b),             # Normalize input b for clean JSON shape.
    "result": normalize_number(result),   # Normalize sum (e.g., 3.0 -> 3).
  }


# Endpoint block: serve the simple HTML home page.
@app.get("/", response_class=HTMLResponse)     # Map HTTP GET / to this handler.
def home() -> HTMLResponse:
  """Return the static home page used in the POC."""
  return HTMLResponse(content=HOME_PAGE_HTML) # Return static HTML content.


# Endpoint block: expose an API health-check for quick availability checks.
@app.get("/api/health")                        # Map HTTP GET /api/health.
def health() -> dict[str, str]:
  """Return a minimal health payload."""
  return {"status": "ok", "app": "test-function-poc"}  # Stable health payload.


# Endpoint block: add two query parameters and return the result.
@app.get("/api/add")                           # Map HTTP GET /api/add.
def add(
  a: float = Query(..., description="First number to add"),   # Required query param a.
  b: float = Query(..., description="Second number to add"),  # Required query param b.
) -> dict[str, int | float]:
  """Add query parameters a and b."""
  return add_numbers(a, b)                    # Delegate to shared helper logic.
