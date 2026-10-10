#!/usr/bin/env python3

import requests
import json
import urllib.parse

# Test different Overpass API endpoints

def test_endpoint(base_url, query, description):
    print(f"\n🧪 Testing {base_url}: {description}")
    
    url = f"{base_url}/api/interpreter"
    
    try:
        # Try GET method
        get_url = f"{url}?data={urllib.parse.quote(query)}"
        response = requests.get(get_url, timeout=10)
        print(f"GET Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ GET Success! Found {len(data.get('elements', []))} elements")
            return True
        
        # Try POST method if GET fails
        response = requests.post(url, data=query, headers={'Content-Type': 'text/plain; charset=utf-8'}, timeout=10)
        print(f"POST Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ POST Success! Found {len(data.get('elements', []))} elements")
            return True
        else:
            print(f"❌ Both methods failed")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    return False

# Simple query
query = """[out:json];
node["amenity"="restaurant"];
around:1000,40.7589,-73.9851;
out;"""

# Try different Overpass endpoints
endpoints = [
    "https://overpass-api.de",
    "https://overpass.kumi.systems", 
    "https://z.overpass-api.de",
    "https://maps.mail.ru",
]

for endpoint in endpoints:
    success = test_endpoint(endpoint, query, "NYC restaurants")
    if success:
        print(f"🎉 Working endpoint found: {endpoint}")
        break

print("\nTesting status endpoint...")
try:
    response = requests.get("https://overpass-api.de/api/status", timeout=5)
    print(f"Status API: {response.status_code}")
    print(response.text[:200])
except Exception as e:
    print(f"Status check failed: {e}")