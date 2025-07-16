#!/usr/bin/env python3
"""
Test script for Fiware entity data processing with Graphiti integration.
This script tests the complete pipeline from receiving Fiware webhook data
and storing it in Graphiti, to searching and health check.
"""

import json
import requests
from datetime import datetime

def create_test_fiware_data():
    """Create sample Fiware entity data for testing."""
    now = datetime.now().isoformat()
    # Create sample entity data as a plain dict
    entity_data = {
        "id": "urn:ngsi-v2:SolarEnergy:001",
        "type": "SolarEnergy",
        "location": {
            "type": "geo:json",
            "value": {
                "type": "Point",
                "coordinates": [144.9583, -37.8033]
            },
            "metadata": {
                "TimeInstant": {
                    "type": "DateTime",
                    "value": now
                }
            }
        },
        "TimeInstant": {
            "type": "DateTime",
            "value": now,
            "metadata": {}
        },
        # Add dynamic attributes
        "Voltage": {
            "type": "float",
            "value": 220.1,
            "metadata": {
                "TimeInstant": {
                    "type": "DateTime",
                    "value": now
                }
            }
        },
        "current": {
            "type": "Text",
            "value": 89.8,
            "metadata": {
                "TimeInstant": {
                    "type": "DateTime",
                    "value": now
                }
            }
        }
    }
    webhook_data = {
        "subscriptionId": "test-subscription-123",
        "data": [entity_data]
    }
    return webhook_data

def test_fiware_webhook():
    """Test the Fiware webhook endpoint for generic entity data."""
    webhook_dict = create_test_fiware_data()
    try:
        response = requests.post(
            "http://localhost:8000/api/fiware/webhook",
            json=webhook_dict,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        if response.status_code == 200:
            print("✅ Fiware webhook test passed!")
        else:
            print("❌ Fiware webhook test failed!")
    except Exception as e:
        print(f"❌ Error testing Fiware webhook: {e}")

def test_fiware_search():
    """Test the Fiware entity search functionality."""
    try:
        search_data = {
            "query": "solar energy sensors with high voltage",
            "limit": 5
        }
        response = requests.post(
            "http://localhost:8000/api/fiware/search",
            json=search_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"Search Status Code: {response.status_code}")
        resp_json = response.json()
        print(f"Search Response: {resp_json}")
        if response.status_code == 200 and "results" in resp_json:
            print(f"✅ Fiware entity search test passed! Found {len(resp_json['results'])} results.")
        else:
            print(f"❌ Fiware entity search test failed! Error: {resp_json.get('detail')}")
    except Exception as e:
        print(f"❌ Error testing fiware search: {e}")

def test_health_check():
    """Test the Fiware health check endpoint."""
    try:
        response = requests.get("http://localhost:8000/api/fiware/health")
        print(f"Health Check Status Code: {response.status_code}")
        print(f"Health Check Response: {response.json()}")
        if response.status_code == 200:
            print("✅ Fiware health check test passed!")
        else:
            print("❌ Fiware health check test failed!")
    except Exception as e:
        print(f"❌ Error testing health check: {e}")

if __name__ == "__main__":
    print("🧪 Testing Fiware Integration with Graphiti")
    print("=" * 50)
    print("\n1. Testing health check...")
    test_health_check()
    print("\n2. Testing Fiware webhook...")
    test_fiware_webhook()
    print("\n3. Testing Fiware entity search...")
    test_fiware_search()
    print("\n" + "=" * 50)
    print("🏁 Fiware integration tests completed!") 
    print("🏁 Fiware integration tests completed!") 