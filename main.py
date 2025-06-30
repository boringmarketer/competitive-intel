#!/usr/bin/env python3
"""
Competitive Intelligence Tool
Simple script to collect and analyze competitor ads
"""

import json
import requests
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import argparse


class CompetitiveIntel:
    def __init__(self, config_path: str = "config.json"):
        self.config = self.load_config(config_path)
        self.session = requests.Session()
    
    def load_config(self, path: str) -> Dict:
        """Load configuration from JSON file"""
        default_config = {
            "apify": {
                "api_token": ""
            },
            "claude": {
                "api_key": ""
            },
            "brands": {
                "AG1": {
                    "facebook_id": "183869772601",
                    "domain": "drinkag1.com",
                    "active": True
                }
            },
            "analysis": {
                "lookback_days": 7,
                "max_ads_per_brand": 10
            },
            "notifications": {
                "webhook_url": "",
                "enabled": True
            }
        }
        
        try:
            with open(path, 'r') as f:
                config = json.load(f)
            # Merge with defaults
            return {**default_config, **config}
        except FileNotFoundError:
            print(f"Config file {path} not found, creating default...")
            with open(path, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config
    
    def collect_ads(self, brand_name: str, brand_config: Dict) -> List[Dict]:
        """Collect ads for a specific brand using Apify Facebook Ad Library scraper"""
        print(f"📊 Collecting ads for {brand_name}...")
        
        if not self.config["apify"]["api_token"]:
            print("  ❌ Apify API token not configured")
            return []
        
        # Prepare Facebook page URL
        facebook_url = None
        if brand_config.get("facebook_id"):
            facebook_url = f"https://www.facebook.com/{brand_config['facebook_id']}"
        elif brand_config.get("domain"):
            # Try to construct Facebook URL from domain
            facebook_url = f"https://www.facebook.com/{brand_config['domain'].replace('.com', '').replace('.', '')}"
        
        if not facebook_url:
            print("  ❌ No Facebook URL available for this brand")
            return []
        
        print(f"  🔍 Scraping: {facebook_url}")
        
        # Prepare Apify Actor input
        actor_input = {
            "startUrls": [{"url": facebook_url}],
            "resultsLimit": self.config["analysis"]["max_ads_per_brand"],
            "activeStatus": ""  # Get all ads
        }
        
        try:
            # Start Apify Actor
            print("  🚀 Starting Apify actor...")
            
            actor_url = "https://api.apify.com/v2/acts/JJghSZmShuco4j9gJ/runs"
            headers = {
                "Authorization": f"Bearer {self.config['apify']['api_token']}",
                "Content-Type": "application/json"
            }
            
            # Start the actor run
            response = self.session.post(actor_url, json=actor_input, headers=headers, timeout=30)
            
            if response.status_code != 201:
                print(f"  ❌ Failed to start actor: {response.status_code}")
                print(f"  📄 Response: {response.text}")
                return []
            
            run_data = response.json()
            run_id = run_data["data"]["id"]
            
            print(f"  ⏳ Actor run started: {run_id}")
            print("  ⌛ Waiting for completion (max 2 minutes)...")
            
            # Wait for completion (max 2 minutes)
            max_wait = 120  # 2 minutes
            wait_time = 0
            
            while wait_time < max_wait:
                # Check run status
                status_url = f"https://api.apify.com/v2/acts/JJghSZmShuco4j9gJ/runs/{run_id}"
                status_response = self.session.get(status_url, headers=headers, timeout=10)
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    status = status_data["data"]["status"]
                    
                    if status == "SUCCEEDED":
                        print("  ✅ Actor completed successfully")
                        break
                    elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                        print(f"  ❌ Actor failed with status: {status}")
                        return []
                    else:
                        print(f"  ⏳ Status: {status}")
                
                time.sleep(10)  # Wait 10 seconds
                wait_time += 10
            
            if wait_time >= max_wait:
                print("  ⏰ Actor timed out, trying to get partial results...")
            
            # Get results from dataset
            dataset_id = run_data["data"]["defaultDatasetId"]
            dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items"
            
            results_response = self.session.get(dataset_url, headers=headers, timeout=30)
            
            if results_response.status_code == 200:
                ads = results_response.json()
                print(f"  ✅ Found {len(ads)} ads")
                
                # Debug: Show data structure of first ad
                if ads and len(ads) > 0:
                    print(f"  🔍 First ad data structure:")
                    first_ad = ads[0]
                    print(f"    Keys: {list(first_ad.keys())}")
                    # Show some sample values (truncated)
                    for key, value in first_ad.items():
                        if isinstance(value, str) and len(value) > 50:
                            print(f"    {key}: {value[:50]}...")
                        else:
                            print(f"    {key}: {value}")
                        if len(str(value)) > 100:  # Limit debug output
                            break
                
                return ads[:self.config["analysis"]["max_ads_per_brand"]]
            else:
                print(f"  ❌ Failed to get results: {results_response.status_code}")
                return []
                
        except Exception as e:
            print(f"  ❌ Apify request failed: {str(e)}")
            return []
    
    def analyze_with_claude(self, brand_name: str, ads: List[Dict]) -> str:
        """Analyze ads using Claude API"""
        if not ads:
            return f"# {brand_name} Market Status\n\nNo active ads detected. Market opportunity window identified."
        
        print(f"🧠 Analyzing {len(ads)} ads with Claude...")
        
        try:
            # Prepare ad data for analysis (handle both Apify and other formats)
            ad_summary = []
            for ad in ads[:3]:  # Analyze top 3 ads
                # Handle Apify format
                if "adText" in ad:  # Apify format
                    ad_summary.append({
                        "headline": ad.get("headline", "") or ad.get("adText", "")[:100],
                        "body": ad.get("adText", ""),
                        "landing_page": ad.get("link", "") or ad.get("linkUrl", ""),
                        "cta": ad.get("ctaText", ""),
                        "image_url": ad.get("imageUrl", "")
                    })
                else:  # Legacy format (Adyntel)
                    snapshot = ad.get("snapshot", {})
                    ad_summary.append({
                        "headline": snapshot.get("linkTitle") or snapshot.get("title", ""),
                        "body": snapshot.get("body") or snapshot.get("adCreativeBody", ""),
                        "landing_page": snapshot.get("linkUrl", ""),
                        "cta": "",
                        "image_url": ""
                    })
            
            prompt = f"""Analyze these {len(ads)} competitor ads from {brand_name}:

{json.dumps(ad_summary, indent=2)}

Provide a competitive analysis with:
1. Key messaging themes (3-4 bullets)
2. Creative patterns observed
3. 3 specific tactical recommendations for a competitor

Keep analysis concise and actionable - max 300 words."""

            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.config["claude"]["api_key"],
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": 1000,
                    "temperature": 0.3,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                analysis = data["content"][0]["text"]
                print("  ✅ Claude analysis completed")
                return analysis
            else:
                print(f"  ❌ Claude API error: {response.status_code}")
                return self.fallback_analysis(brand_name, ads)
                
        except Exception as e:
            print(f"  ❌ Claude analysis failed: {str(e)}")
            return self.fallback_analysis(brand_name, ads)
    
    def fallback_analysis(self, brand_name: str, ads: List[Dict]) -> str:
        """Generate smart fallback analysis using real ad data"""
        print("  🔄 Using fallback analysis...")
        
        headlines = []
        bodies = []
        landing_pages = []
        
        for ad in ads:
            # Handle Apify format
            if "adText" in ad:  # Apify format
                if headline := ad.get("headline") or ad.get("adText", "")[:100]:
                    headlines.append(headline)
                if body := ad.get("adText"):
                    bodies.append(body)
                if url := ad.get("link") or ad.get("linkUrl"):
                    landing_pages.append(url)
            else:  # Legacy format (Adyntel)
                snapshot = ad.get("snapshot", {})
                if headline := snapshot.get("linkTitle") or snapshot.get("title"):
                    headlines.append(headline)
                if body := snapshot.get("body") or snapshot.get("adCreativeBody"):
                    bodies.append(body)
                if url := snapshot.get("linkUrl"):
                    landing_pages.append(url)
        
        # Extract themes from ad text
        all_text = " ".join(headlines + bodies).lower()
        themes = {
            "science": any(word in all_text for word in ["clinical", "research", "study", "proven", "science"]),
            "convenience": any(word in all_text for word in ["simple", "easy", "daily", "one scoop"]),
            "energy": any(word in all_text for word in ["energy", "boost", "performance", "vitality"]),
            "health": any(word in all_text for word in ["health", "wellness", "nutrition", "vitamin"])
        }
        
        analysis = f"""# {brand_name} Competitive Analysis (Real Data)

## 📊 Collection Summary
- **{len(ads)} active ads** collected
- **{len(headlines)} headlines** analyzed
- **{len(landing_pages)} landing pages** identified

## 🎯 Top Headlines
{chr(10).join(f"• \"{h}\"" for h in headlines[:3])}

## 📈 Messaging Themes
- **Scientific Authority**: {"✅ Strong focus" if themes["science"] else "⚠️ Limited claims"}
- **Convenience**: {"✅ Simplicity messaging" if themes["convenience"] else "⚠️ Complex positioning"}
- **Energy/Performance**: {"✅ Performance focus" if themes["energy"] else "⚠️ Limited energy claims"}
- **Health Focus**: {"✅ Wellness-centered" if themes["health"] else "⚠️ Non-health positioning"}

## 💡 Tactical Recommendations
1. **Test Top Performers**: A/B test variations of their best headlines
2. **Landing Page Review**: Analyze {len(landing_pages)} destination pages for conversion elements
3. **Competitive Positioning**: Position against their key messaging themes

**Analysis of {len(ads)} live {brand_name} ads - {datetime.now().strftime("%Y-%m-%d")}**"""
        
        return analysis
    
    def send_notification(self, report: str) -> bool:
        """Send report via webhook (Pipedream → Slack)"""
        if not self.config["notifications"]["enabled"] or not self.config["notifications"]["webhook_url"]:
            print("📱 Notifications disabled or no webhook URL")
            return False
        
        print("📱 Sending notification...")
        
        try:
            response = requests.post(
                self.config["notifications"]["webhook_url"],
                json={
                    "report": report,
                    "timestamp": datetime.now().isoformat(),
                    "source": "competitive-intel-tool"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                print("  ✅ Notification sent successfully")
                return True
            else:
                print(f"  ❌ Notification failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"  ❌ Notification error: {str(e)}")
            return False
    
    def save_report(self, report: str, brand_name: str = "all") -> str:
        """Save report to file"""
        os.makedirs("reports", exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reports/{brand_name}_{timestamp}.md"
        
        with open(filename, 'w') as f:
            f.write(report)
        
        print(f"💾 Report saved: {filename}")
        return filename
    
    def run_analysis(self, brand_filter: Optional[str] = None) -> str:
        """Run complete competitive analysis"""
        print("🚀 Starting Competitive Intelligence Analysis...")
        
        # Filter brands if specified
        active_brands = {
            name: config for name, config in self.config["brands"].items()
            if config.get("active", True) and (not brand_filter or name == brand_filter)
        }
        
        if not active_brands:
            print(f"❌ No active brands found{f' matching \"{brand_filter}\"' if brand_filter else ''}")
            return ""
        
        print(f"🎯 Analyzing {len(active_brands)} brands: {', '.join(active_brands.keys())}")
        
        # Generate report header
        report_date = datetime.now().strftime("%A, %B %d, %Y")
        report = f"""# 🎯 Competitive Intelligence Report - {report_date}

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

"""
        
        # Analyze each brand
        total_ads = 0
        for brand_name, brand_config in active_brands.items():
            print(f"\n--- Analyzing {brand_name} ---")
            
            # Collect ads
            ads = self.collect_ads(brand_name, brand_config)
            total_ads += len(ads)
            
            # Analyze with Claude
            analysis = self.analyze_with_claude(brand_name, ads)
            
            # Add to report
            report += f"{analysis}\n\n---\n\n"
        
        # Add summary footer
        report += f"""## 📊 Analysis Summary
- **Brands Analyzed**: {len(active_brands)}
- **Total Ads Collected**: {total_ads}
- **Analysis Date**: {report_date}
- **Tool**: Competitive Intel v1.0

*Next analysis recommended in 7 days*"""
        
        print(f"\n🎉 Analysis completed! {total_ads} ads analyzed across {len(active_brands)} brands")
        
        # Save report
        filename = self.save_report(report, brand_filter or "all")
        
        # Send notification
        self.send_notification(report)
        
        return report


def main():
    parser = argparse.ArgumentParser(description="Run competitive intelligence analysis")
    parser.add_argument("--brand", help="Analyze specific brand only")
    parser.add_argument("--config", default="config.json", help="Config file path")
    parser.add_argument("--no-notify", action="store_true", help="Skip notifications")
    
    args = parser.parse_args()
    
    # Initialize tool
    intel = CompetitiveIntel(args.config)
    
    # Disable notifications if requested
    if args.no_notify:
        intel.config["notifications"]["enabled"] = False
    
    # Run analysis
    try:
        report = intel.run_analysis(args.brand)
        if report:
            print(f"\n📄 Report preview:")
            print("=" * 50)
            print(report[:500] + "..." if len(report) > 500 else report)
    except KeyboardInterrupt:
        print("\n🛑 Analysis interrupted by user")
    except Exception as e:
        print(f"\n❌ Analysis failed: {str(e)}")


if __name__ == "__main__":
    main()