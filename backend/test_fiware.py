#!/usr/bin/env python3
"""
Test script for Fiware sensor data processing with Graphiti integration.
This script tests the complete pipeline from receiving Fiware webhook data
to storing it in Graphiti and creating embeddings.
"""

import json
import requests
from datetime import datetime
from models import FiwareWebhookData, FiwareSensorData, SensorLocation, GeoJsonPoint, TimeInstant, SensorMetadata

def create_test_fiware_data():
    """Create sample Fiware sensor data for testing."""
    
    # Create sample sensor data
    sensor_data = FiwareSensorData(root={
        "id": "urn:ngsi-v2:SolarEnergy:001",
        "type": "SolarEnergy",
        "location": SensorLocation(
            type="geo:json",
            value=GeoJsonPoint(
                type="Point",
                coordinates=[144.9583, -37.8033]
            ),
            metadata=SensorMetadata(
                TimeInstant=TimeInstant(
                    type="DateTime",
                    value=datetime.now()
                )
            )
        ),
        "TimeInstant": TimeInstant(
            type="DateTime",
            value=datetime.now()
        ),
        # Add dynamic attributes
        "Voltage": {
            "type": "float",
            "value": 220.1,
            "metadata": {
                "TimeInstant": {
                    "type": "DateTime",
                    "value": datetime.now()  # Use datetime object, not string
                }
            }
        },
        "current": {
            "type": "Text",
            "value": 89.8,
            "metadata": {
                "TimeInstant": {
                    "type": "DateTime",
                    "value": datetime.now()  # Use datetime object, not string
                }
            }
        }
    })
    
    # Create webhook data
    webhook_data = FiwareWebhookData(
        subscriptionId="test-subscription-123",
        data=[sensor_data]
    )
    
    return webhook_data

def convert_datetimes(obj):
    if isinstance(obj, dict):
        return {k: convert_datetimes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetimes(i) for i in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj

def test_fiware_webhook():
    """Test the Fiware webhook endpoint for generic entity data."""
    
    # Create test data
    webhook_data = create_test_fiware_data()
    
    # Convert to dict for API call
    webhook_dict = {
        "subscriptionId": webhook_data.subscriptionId,
        "data": [
            {
                "id": webhook_data.data[0].root["id"],
                "type": webhook_data.data[0].root["type"],
                "location": {
                    "type": webhook_data.data[0].root["location"].type,
                    "value": {
                        "type": webhook_data.data[0].root["location"].value.type,
                        "coordinates": webhook_data.data[0].root["location"].value.coordinates
                    },
                    "metadata": {
                        "TimeInstant": {
                            "type": "DateTime",
                            "value": webhook_data.data[0].root["location"].metadata.TimeInstant.value.isoformat()
                        }
                    }
                },
                "TimeInstant": {
                    "type": "DateTime",
                    "value": webhook_data.data[0].root["TimeInstant"].value.isoformat(),
                    "metadata": {}
                },
                "Voltage": webhook_data.data[0].root["Voltage"],
                "current": webhook_data.data[0].root["current"]
            }
        ]
    }
    webhook_dict = convert_datetimes(webhook_dict)
    
    # Send to API
    try:
        response = requests.post(
            "http://localhost:8000/api/fiware/webhook",
            json=webhook_dict,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Output: update to entity
        if response.status_code == 200:
            print("✅ Fiware webhook test passed!")
        else:
            print("❌ Fiware webhook test failed!")
            
    except Exception as e:
        print(f"❌ Error testing Fiware webhook: {e}")

def test_sensor_search():
    """Test the Fiware entity search functionality."""
    
    try:
        # Test search query
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
        print(f"Search Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Fiware entity search test passed!")
        else:
            print("❌ Fiware entity search test failed!")
            
    except Exception as e:
        print(f"❌ Error testing sensor search: {e}")

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
    
    # Test health check first
    print("\n1. Testing health check...")
    test_health_check()
    
    # Test webhook
    print("\n2. Testing Fiware webhook...")
    test_fiware_webhook()
    
    # Test search
    print("\n3. Testing Fiware entity search...")
    test_sensor_search()
    
    print("\n" + "=" * 50)
    print("🏁 Fiware integration tests completed!") 