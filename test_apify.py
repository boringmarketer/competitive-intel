#!/usr/bin/env python3
"""
Test Apify Facebook Ad Library scraper directly
to confirm API access and see data format
"""

import requests
import json
import time
import sys

def test_apify_api(api_token, facebook_url="https://www.facebook.com/183869772601"):
    """Test Apify Facebook Ad Library scraper"""
    
    print(f"🧪 Testing Apify API...")
    print(f"📱 Facebook URL: {facebook_url}")
    print(f"🔑 API Token: {api_token[:10]}...")
    
    # Prepare Actor input
    actor_input = {
        "startUrls": [{"url": facebook_url}],
        "resultsLimit": 5,  # Just get a few for testing
        "activeStatus": ""  # Get all ads
    }
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    try:
        # Start the actor
        print("\n🚀 Starting Apify actor...")
        actor_url = "https://api.apify.com/v2/acts/JJghSZmShuco4j9gJ/runs"
        
        response = requests.post(actor_url, json=actor_input, headers=headers, timeout=30)
        
        print(f"📥 Start response: {response.status_code}")
        
        if response.status_code != 201:
            print(f"❌ Failed to start actor")
            print(f"📄 Response: {response.text}")
            return False
        
        run_data = response.json()
        run_id = run_data["data"]["id"]
        
        print(f"✅ Actor started successfully")
        print(f"🔍 Run ID: {run_id}")
        print(f"⏳ Waiting for completion...")
        
        # Wait for completion (max 3 minutes for testing)
        max_wait = 180
        wait_time = 0
        
        while wait_time < max_wait:
            # Check status
            status_url = f"https://api.apify.com/v2/acts/JJghSZmShuco4j9gJ/runs/{run_id}"
            status_response = requests.get(status_url, headers=headers, timeout=10)
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                status = status_data["data"]["status"]
                
                print(f"📊 Status: {status}")
                
                if status == "SUCCEEDED":
                    print("✅ Actor completed successfully!")
                    break
                elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                    print(f"❌ Actor failed: {status}")
                    return False
            
            time.sleep(15)  # Wait 15 seconds
            wait_time += 15
        
        if wait_time >= max_wait:
            print("⏰ Timeout - getting partial results...")
        
        # Get results
        print("\n📊 Fetching results...")
        dataset_id = run_data["data"]["defaultDatasetId"]
        dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items"
        
        results_response = requests.get(dataset_url, headers=headers, timeout=30)
        
        if results_response.status_code == 200:
            ads = results_response.json()
            print(f"✅ Retrieved {len(ads)} ads")
            
            if ads:
                print("\n🔍 FIRST AD DATA STRUCTURE:")
                first_ad = ads[0]
                print(f"📋 Available keys: {list(first_ad.keys())}")
                
                print(f"\n📄 SAMPLE AD DATA:")
                for key, value in first_ad.items():
                    if isinstance(value, str):
                        if len(value) > 100:
                            print(f"  {key}: {value[:100]}...")
                        else:
                            print(f"  {key}: {value}")
                    else:
                        print(f"  {key}: {value}")
                
                # Show a few more ads for patterns
                if len(ads) > 1:
                    print(f"\n📊 CHECKING {min(3, len(ads))} ADS FOR PATTERNS:")
                    for i, ad in enumerate(ads[:3]):
                        print(f"\nAd {i+1}:")
                        print(f"  Keys: {list(ad.keys())}")
                        if 'adText' in ad:
                            print(f"  Text: {ad['adText'][:50]}...")
                        if 'headline' in ad:
                            print(f"  Headline: {ad.get('headline', 'N/A')}")
                        if 'link' in ad:
                            print(f"  Link: {ad.get('link', 'N/A')}")
                
                return True
            else:
                print("❌ No ads returned from Apify")
                return False
        else:
            print(f"❌ Failed to get results: {results_response.status_code}")
            print(f"📄 Response: {results_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Get API token from command line or prompt
    if len(sys.argv) > 1:
        api_token = sys.argv[1]
    else:
        api_token = input("Enter your Apify API token: ").strip()
    
    if not api_token:
        print("❌ No API token provided")
        sys.exit(1)
    
    # Test different Facebook URLs
    test_urls = [
        "https://www.facebook.com/183869772601",  # AG1
        "https://www.facebook.com/drinkag1",      # AG1 alternate
        "https://www.facebook.com/107585658730958"  # Gruns Daily
    ]
    
    for url in test_urls:
        print(f"\n{'='*60}")
        success = test_apify_api(api_token, url)
        if success:
            print(f"✅ SUCCESS with {url}")
            break
        else:
            print(f"❌ FAILED with {url}")
    else:
        print(f"\n❌ All test URLs failed")
        print(f"💡 Try checking:")
        print(f"   - API token is valid")
        print(f"   - Facebook page URLs are correct")
        print(f"   - Apify actor JJghSZmShuco4j9gJ is working")