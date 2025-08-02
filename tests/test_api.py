#!/usr/bin/env python
"""Test script for AutoTrainX API."""

import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(endpoint, method="GET", data=None):
    """Test an API endpoint."""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        else:
            print(f"Unsupported method: {method}")
            return
        
        print(f"\n{method} {endpoint}")
        print(f"Status: {response.status_code}")
        
        try:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except:
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"\nError: Cannot connect to API server at {BASE_URL}")
        print("Make sure the server is running with: python api_server.py --dev")
        sys.exit(1)
    except Exception as e:
        print(f"\nError testing {endpoint}: {e}")

def main():
    """Run API tests."""
    print("Testing AutoTrainX API endpoints...")
    
    # Test health endpoint
    test_endpoint("/health")
    
    # Test root endpoint
    test_endpoint("/")
    
    # Test jobs endpoint
    test_endpoint("/api/v1/jobs")
    
    # Test presets endpoint
    test_endpoint("/api/v1/presets")
    
    # Test datasets endpoint
    test_endpoint("/api/v1/datasets")
    
    # Test a POST endpoint
    print("\n\nTesting training creation...")
    test_endpoint("/api/v1/training/single", "POST", {
        "dataset_name": "test_dataset",
        "preset": "FluxLORA",
        "auto_start": False
    })

if __name__ == "__main__":
    main()