import requests
import json

def test_endpoint(endpoint):
    url = f"http://localhost:8000{endpoint}"
    try:
        response = requests.get(url)
        print(f"\nTesting endpoint: {url}")
        print(f"Status code: {response.status_code}")
        print("Response:")
        print(json.dumps(response.json(), indent=2))
        return response.status_code == 200
    except Exception as e:
        print(f"Error testing endpoint {endpoint}: {e}")
        return False

if __name__ == "__main__":
    endpoints = [
        "/health",
        "/map",
        "/system/status",
        "/taxis",
        "/requests/pending"
    ]

    for endpoint in endpoints:
        test_endpoint(endpoint)