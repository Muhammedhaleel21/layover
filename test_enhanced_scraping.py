#!/usr/bin/env python3
"""Test enhanced OpenStreetMap scraping with 5km radius and comprehensive place data."""

import json
import requests
import sys

API_BASE = "http://localhost:8001"

def test_comprehensive_scraping():
    """Test comprehensive place scraping for different styles."""
    
    # Test locations (you can modify coordinates for your current location)
    test_locations = [
        {
            "name": "Kozhikode (Current Test Location)",
            "lat": 11.2476,
            "lng": 75.7836,
            "description": "Railway station area in Kozhikode, Kerala"
        }
        # Add your current location here:
        # {
        #     "name": "Your Current Location",
        #     "lat": YOUR_LATITUDE,
        #     "lng": YOUR_LONGITUDE,
        #     "description": "Your current area description"
        # }
    ]
    
    styles = ["history", "food", "culture", "nature", "mixed"]
    
    for location in test_locations:
        print(f"\n{'='*80}")
        print(f"COMPREHENSIVE SCRAPING TEST: {location['name']}")
        print(f"Location: {location['lat']}, {location['lng']}")
        print(f"Description: {location['description']}")
        print(f"{'='*80}")
        
        for style in styles:
            print(f"\n--- {style.upper()} PLACES (5km+ radius) ---")
            
            request_data = {
                "start": location["name"],
                "start_lat": location["lat"],
                "start_lng": location["lng"],
                "minutes": 300,  # 5 hours for large radius
                "budget": 2000,
                "buffer": 30,
                "mode": "both",
                "style": style,
                "difficulty": "medium"
            }
            
            try:
                response = requests.post(f"{API_BASE}/api/adventures", json=request_data)
                
                if response.status_code == 200:
                    data = response.json()
                    missions = data.get('missions', [])
                    
                    print(f"Found {len(missions)} places")
                    
                    # Display detailed information about each place
                    for i, mission in enumerate(missions, 1):
                        print(f"\n{i}. {mission['name']}")
                        print(f"   📍 Coordinates: ({mission['lat']}, {mission['lng']})")
                        print(f"   🏷️  Categories: {', '.join(mission.get('categories', ['mixed']))}")
                        print(f"   ⏱️  Travel: {mission['travelMin']}min | Visit: {mission['visitMin']}min | Return: {mission['returnMin']}min")
                        print(f"   💰 Estimated cost: ₹{mission['cost']}")
                        print(f"   📝 Title: {mission['title']}")
                        
                        # Show some facts if available (these come from OSM tags)
                        if 'facts' in mission and mission['facts']:
                            print(f"   📊 Facts from OpenStreetMap:")
                            for fact in mission['facts'][:3]:  # Show first 3 facts
                                print(f"      • {fact}")
                            if len(mission['facts']) > 3:
                                print(f"      ... and {len(mission['facts']) - 3} more facts")
                    
                    if not missions:
                        print("   No places found matching criteria within time/budget constraints")
                        
                else:
                    print(f"   Error {response.status_code}: {response.text}")
                    
            except Exception as e:
                print(f"   Error: {e}")
        
        print(f"\n{'='*80}")

def test_current_location_scraping():
    """Interactive test to scrape places around user's current location."""
    print("\n🌍 CURRENT LOCATION SCRAPING TEST")
    print("To test with your actual current location, please:")
    print("1. Get your current GPS coordinates")
    print("2. Update the coordinates in this script")
    print("3. Run the test again")
    
    # You can update these coordinates to your current location
    current_lat = input("\nEnter your current latitude (or press Enter for Kozhikode): ").strip()
    current_lng = input("Enter your current longitude (or press Enter for Kozhikode): ").strip()
    
    if not current_lat or not current_lng:
        current_lat, current_lng = 11.2476, 75.7836
        location_name = "Kozhikode Railway Station (Demo)"
    else:
        current_lat, current_lng = float(current_lat), float(current_lng)
        location_name = "Your Current Location"
    
    print(f"\n🔍 Scraping comprehensive data within 5km radius of:")
    print(f"📍 {location_name}: {current_lat}, {current_lng}")
    
    # Test with mixed style for comprehensive results
    request_data = {
        "start": location_name,
        "start_lat": current_lat,
        "start_lng": current_lng,
        "minutes": 400,  # Large time allowance for 5km+ radius
        "budget": 3000,  # Large budget
        "buffer": 30,
        "mode": "both",
        "style": "mixed",  # Get all types of places
        "difficulty": "medium"
    }
    
    try:
        print("\n⏳ Querying OpenStreetMap Overpass API...")
        response = requests.post(f"{API_BASE}/api/adventures", json=request_data)
        
        if response.status_code == 200:
            data = response.json()
            missions = data.get('missions', [])
            
            print(f"\n✅ SUCCESS! Found {len(missions)} places within 5km radius")
            print(f"🗃️  Data source: {data.get('source', 'unknown')}")
            
            # Categorize results
            categories = {}
            for mission in missions:
                for cat in mission.get('categories', ['mixed']):
                    if cat not in categories:
                        categories[cat] = []
                    categories[cat].append(mission)
            
            print(f"\n📊 BREAKDOWN BY CATEGORY:")
            for category, places in categories.items():
                print(f"   {category.upper()}: {len(places)} places")
            
            print(f"\n🎯 TOP 10 NEARBY PLACES:")
            for i, mission in enumerate(missions[:10], 1):
                distance_est = mission['travelMin'] * 0.5  # Rough km estimate
                print(f"{i:2}. {mission['name']}")
                print(f"    📍 ~{distance_est:.1f}km away | ⏱️ {mission['travelMin']}min travel")
                print(f"    🏷️  {', '.join(mission.get('categories', ['general']))}")
                
                # Show a sample fact
                if 'facts' in mission and mission['facts']:
                    sample_fact = mission['facts'][0]
                    if len(sample_fact) > 60:
                        sample_fact = sample_fact[:57] + "..."
                    print(f"    📝 {sample_fact}")
                print()
            
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Run comprehensive scraping tests."""
    print("🗺️  ENHANCED OPENSTREETMAP SCRAPING TEST")
    print("=" * 60)
    
    # Check if backend is running
    try:
        health = requests.get(f"{API_BASE}/api/health", timeout=5)
        if health.status_code != 200:
            print("❌ Backend API not available. Please start the backend server first.")
            return
    except:
        print("❌ Backend API not reachable. Please start the backend server first.")
        print("   Run: cd backend && python simple_main.py")
        return
    
    print("✅ Backend API is running")
    
    # Run tests
    if len(sys.argv) > 1 and sys.argv[1] == "--current":
        test_current_location_scraping()
    else:
        test_comprehensive_scraping()
        print(f"\n💡 TIP: Use '--current' flag to test with your actual GPS location")
        print("   python test_enhanced_scraping.py --current")

if __name__ == "__main__":
    main()