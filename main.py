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
from typing import Dict, List, Optional, Tuple
import argparse


class CompetitiveIntel:
    def __init__(self, config_path: str = None):
        if config_path:
            self.config = self.load_config(config_path)
        else:
            # Will be set externally (e.g., from Streamlit)
            self.config = None
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
    
    def extract_ad_insights(self, ads: List[Dict]) -> Dict:
        """Extract structured insights from ads for visualization"""
        insights = {
            "media_distribution": {"video": 0, "image": 0, "text_only": 0},
            "platform_distribution": {},
            "cta_types": {},
            "themes": {
                "science": 0, "convenience": 0, "energy": 0, "health": 0,
                "premium": 0, "social_proof": 0, "urgency": 0
            },
            "performance_indicators": {
                "active_ads": 0,
                "total_ads": len(ads),
                "avg_days_running": 0,
                "unique_headlines": 0,
                "unique_landing_pages": 0
            },
            "raw_data": {
                "headlines": [],
                "bodies": [],
                "ctas": [],
                "landing_pages": [],
                "platforms": []
            }
        }
        
        headlines_set = set()
        landing_pages_set = set()
        total_days = 0
        active_count = 0
        
        for ad in ads:
            # Handle Apify Facebook Ad Library format
            if "snapshot" in ad and "cards" in ad.get("snapshot", {}):
                snapshot = ad["snapshot"]
                cards = snapshot.get("cards", [])
                
                if cards:
                    card = cards[0]
                    
                    # Media type analysis
                    if card.get("videoHdUrl") or card.get("videoSdUrl"):
                        insights["media_distribution"]["video"] += 1
                    elif card.get("originalImageUrl"):
                        insights["media_distribution"]["image"] += 1
                    else:
                        insights["media_distribution"]["text_only"] += 1
                    
                    # Extract text content
                    headline = card.get("title", "") or snapshot.get("title", "")
                    body = card.get("body", "") or snapshot.get("body", {}).get("text", "")
                    cta = card.get("ctaText", "")
                    landing_page = card.get("linkUrl", "") or snapshot.get("linkUrl", "")
                    
                    if headline:
                        headlines_set.add(headline)
                        insights["raw_data"]["headlines"].append(headline)
                    if body:
                        insights["raw_data"]["bodies"].append(body)
                    if cta:
                        insights["cta_types"][cta] = insights["cta_types"].get(cta, 0) + 1
                        insights["raw_data"]["ctas"].append(cta)
                    if landing_page:
                        landing_pages_set.add(landing_page)
                        insights["raw_data"]["landing_pages"].append(landing_page)
                    
                    # Theme analysis
                    all_text = f"{headline} {body}".lower()
                    if any(word in all_text for word in ["clinical", "research", "study", "proven", "science", "doctor"]):
                        insights["themes"]["science"] += 1
                    if any(word in all_text for word in ["simple", "easy", "daily", "one scoop", "convenient"]):
                        insights["themes"]["convenience"] += 1
                    if any(word in all_text for word in ["energy", "boost", "performance", "vitality", "focus"]):
                        insights["themes"]["energy"] += 1
                    if any(word in all_text for word in ["health", "wellness", "nutrition", "vitamin", "immune"]):
                        insights["themes"]["health"] += 1
                    if any(word in all_text for word in ["premium", "quality", "best", "superior", "luxury"]):
                        insights["themes"]["premium"] += 1
                    if any(word in all_text for word in ["customers", "reviews", "testimonial", "loved", "rated"]):
                        insights["themes"]["social_proof"] += 1
                    if any(word in all_text for word in ["limited", "now", "today", "hurry", "expires"]):
                        insights["themes"]["urgency"] += 1
                
                # Platform analysis
                platforms = ad.get("publisherPlatform", [])
                for platform in platforms:
                    insights["platform_distribution"][platform] = insights["platform_distribution"].get(platform, 0) + 1
                    insights["raw_data"]["platforms"].append(platform)
                
                # Performance indicators
                if ad.get("isActive"):
                    active_count += 1
                
                total_time = ad.get("totalActiveTime", 0)
                if total_time:
                    days = total_time // (24 * 3600)
                    total_days += days
        
        # Calculate averages
        insights["performance_indicators"]["active_ads"] = active_count
        insights["performance_indicators"]["unique_headlines"] = len(headlines_set)
        insights["performance_indicators"]["unique_landing_pages"] = len(landing_pages_set)
        insights["performance_indicators"]["avg_days_running"] = total_days // len(ads) if ads else 0
        
        return insights
    
    def analyze_with_claude(self, brand_name: str, ads: List[Dict]) -> Tuple[str, Dict]:
        """Analyze ads using Claude API"""
        # Extract structured insights first
        insights = self.extract_ad_insights(ads)
        
        if not ads:
            return f"# {brand_name} Market Status\n\nNo active ads detected. Market opportunity window identified.", insights
        
        print(f"🧠 Analyzing {len(ads)} ads with Claude...")
        
        try:
            # Prepare enhanced ad data for strategic analysis
            ad_summary = []
            for i, ad in enumerate(ads[:5]):  # Analyze top 5 ads for better insights
                # Handle Apify Facebook Ad Library format
                if "snapshot" in ad and "cards" in ad.get("snapshot", {}):  # Apify format
                    snapshot = ad["snapshot"]
                    cards = snapshot.get("cards", [])
                    
                    if cards:
                        # Get data from first card
                        card = cards[0]
                        
                        # Determine media type and URLs
                        media_type = "text_only"
                        media_urls = []
                        
                        if card.get("videoHdUrl") or card.get("videoSdUrl"):
                            media_type = "video"
                            media_urls = [url for url in [
                                card.get("videoHdUrl"),
                                card.get("videoSdUrl"),
                                card.get("videoPreviewImageUrl")
                            ] if url]
                        elif card.get("originalImageUrl"):
                            media_type = "image"
                            media_urls = [url for url in [
                                card.get("originalImageUrl"),
                                card.get("resizedImageUrl")
                            ] if url]
                        
                        # Extract performance and targeting indicators
                        platforms = ad.get("publisherPlatform", [])
                        is_active = ad.get("isActive", False)
                        start_date = ad.get("startDateFormatted", "")
                        total_time = ad.get("totalActiveTime", 0)
                        
                        ad_summary.append({
                            "ad_id": ad.get("adArchiveId", f"unknown_{i}"),
                            "headline": card.get("title", "") or snapshot.get("title", ""),
                            "body_text": card.get("body", "") or snapshot.get("body", {}).get("text", ""),
                            "landing_page": card.get("linkUrl", "") or snapshot.get("linkUrl", ""),
                            "cta_text": card.get("ctaText", "") or snapshot.get("ctaText", ""),
                            "cta_type": card.get("ctaType", ""),
                            "link_description": card.get("linkDescription", ""),
                            
                            # Creative Analysis
                            "media_type": media_type,
                            "media_urls": media_urls,
                            "contains_ai_content": ad.get("containsDigitalCreatedMedia", False),
                            "display_format": snapshot.get("displayFormat", ""),
                            
                            # Platform & Performance
                            "platforms": platforms,
                            "is_active": is_active,
                            "start_date": start_date,
                            "days_running": total_time // (24 * 3600) if total_time else 0,
                            
                            # Brand Context
                            "page_name": ad.get("pageName", ""),
                            "page_category": snapshot.get("pageCategories", []),
                            "page_likes": snapshot.get("pageLikeCount", 0),
                            
                            # Competitive Intelligence
                            "ad_archive_url": f"https://www.facebook.com/ads/library/?id={ad.get('adArchiveId', '')}"
                        })
                    else:
                        # Fallback to snapshot data
                        ad_summary.append({
                            "ad_id": ad.get("adArchiveId", f"unknown_{i}"),
                            "headline": snapshot.get("title", ""),
                            "body_text": snapshot.get("body", {}).get("text", "") if isinstance(snapshot.get("body"), dict) else str(snapshot.get("body", "")),
                            "landing_page": snapshot.get("linkUrl", ""),
                            "cta_text": snapshot.get("ctaText", ""),
                            "media_type": "unknown",
                            "platforms": ad.get("publisherPlatform", []),
                            "page_name": ad.get("pageName", "")
                        })
                else:  # Legacy format (Adyntel or other)
                    snapshot = ad.get("snapshot", {})
                    ad_summary.append({
                        "ad_id": f"legacy_{i}",
                        "headline": snapshot.get("linkTitle") or snapshot.get("title", ""),
                        "body_text": snapshot.get("body") or snapshot.get("adCreativeBody", ""),
                        "landing_page": snapshot.get("linkUrl", ""),
                        "cta_text": "",
                        "media_type": "unknown",
                        "platforms": ["facebook"],
                        "page_name": ad.get("pageName", "")
                    })
            
            prompt = f"""Analyze these {len(ads)} competitor ads from {brand_name} for strategic competitive intelligence:

{json.dumps(ad_summary, indent=2)}

Provide comprehensive competitive analysis with:

## MESSAGING STRATEGY ANALYSIS
- Dominant value propositions and positioning themes
- Language patterns and emotional triggers used
- Target audience signals from copy tone and style
- Unique selling proposition differentiation

## CREATIVE STRATEGY INSIGHTS  
- Media format distribution (video vs image vs text)
- Visual creative patterns and design themes
- CTA strategies and conversion optimization approaches
- Cross-platform creative adaptation patterns

## PERFORMANCE INDICATORS
- Campaign longevity and testing patterns (days running)
- Platform distribution strategy (FB/IG/Audience Network)
- Creative iteration and optimization signals
- Landing page funnel strategy analysis

## COMPETITIVE GAPS & OPPORTUNITIES
- Messaging angles they're NOT using
- Creative formats they're underutilizing  
- Platform opportunities they're missing
- Audience segments that appear underserved

## TACTICAL COUNTERMOVES
- 5 specific copy variations to test against their messaging
- 3 creative format recommendations to differentiate
- 2 platform strategy adjustments to outmaneuver them
- 1 unique positioning angle to exploit their weaknesses

Focus on actionable intelligence for immediate competitive advantage."""

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
                return analysis, insights
            else:
                print(f"  ❌ Claude API error: {response.status_code}")
                return self.fallback_analysis(brand_name, ads), insights
                
        except Exception as e:
            print(f"  ❌ Claude analysis failed: {str(e)}")
            return self.fallback_analysis(brand_name, ads), insights
    
    def fallback_analysis(self, brand_name: str, ads: List[Dict]) -> str:
        """Generate smart fallback analysis using real ad data"""
        print("  🔄 Using fallback analysis...")
        
        headlines = []
        bodies = []
        landing_pages = []
        
        # Extract data for analysis using same structure as main analysis
        media_types = {"video": 0, "image": 0, "text_only": 0}
        platforms_used = set()
        cta_types = []
        active_ads = 0
        
        for ad in ads:
            # Handle Apify Facebook Ad Library format
            if "snapshot" in ad and "cards" in ad.get("snapshot", {}):  # Apify format
                snapshot = ad["snapshot"]
                cards = snapshot.get("cards", [])
                
                if cards:
                    # Get data from first card
                    card = cards[0]
                    if headline := card.get("title", "") or snapshot.get("title", ""):
                        headlines.append(headline)
                    if body := card.get("body", "") or snapshot.get("body", {}).get("text", ""):
                        bodies.append(body)
                    if url := card.get("linkUrl", "") or snapshot.get("linkUrl", ""):
                        landing_pages.append(url)
                    
                    # Track media types
                    if card.get("videoHdUrl") or card.get("videoSdUrl"):
                        media_types["video"] += 1
                    elif card.get("originalImageUrl"):
                        media_types["image"] += 1
                    else:
                        media_types["text_only"] += 1
                    
                    # Track CTAs
                    if cta := card.get("ctaText", ""):
                        cta_types.append(cta)
                        
                else:
                    # Fallback to snapshot data
                    if headline := snapshot.get("title", ""):
                        headlines.append(headline)
                    if body := snapshot.get("body", {}).get("text", "") if isinstance(snapshot.get("body"), dict) else str(snapshot.get("body", "")):
                        bodies.append(body)
                    if url := snapshot.get("linkUrl", ""):
                        landing_pages.append(url)
                
                # Track platforms and activity
                platforms_used.update(ad.get("publisherPlatform", []))
                if ad.get("isActive"):
                    active_ads += 1
                    
            else:  # Legacy format (Adyntel or other)
                snapshot = ad.get("snapshot", {})
                if headline := snapshot.get("linkTitle") or snapshot.get("title"):
                    headlines.append(headline)
                if body := snapshot.get("body") or snapshot.get("adCreativeBody"):
                    bodies.append(body)
                if url := snapshot.get("linkUrl"):
                    landing_pages.append(url)
                platforms_used.add("FACEBOOK")
        
        # Extract themes from ad text
        all_text = " ".join(headlines + bodies).lower()
        themes = {
            "science": any(word in all_text for word in ["clinical", "research", "study", "proven", "science"]),
            "convenience": any(word in all_text for word in ["simple", "easy", "daily", "one scoop"]),
            "energy": any(word in all_text for word in ["energy", "boost", "performance", "vitality"]),
            "health": any(word in all_text for word in ["health", "wellness", "nutrition", "vitamin"])
        }
        
        # Get dominant media type and platform insights
        dominant_media = max(media_types, key=media_types.get) if any(media_types.values()) else "unknown"
        dominant_cta = max(set(cta_types), key=cta_types.count) if cta_types else "No CTA"
        platform_list = list(platforms_used) if platforms_used else ["Unknown"]
        
        analysis = f"""# {brand_name} Competitive Intelligence Analysis

## 📊 Campaign Overview
- **{len(ads)} active ads** collected from {brand_name}
- **{active_ads}/{len(ads)} currently active** ({int(active_ads/len(ads)*100) if ads else 0}% active rate)
- **{len(headlines)} unique headlines** analyzed
- **{len(landing_pages)} landing pages** identified
- **Platforms**: {', '.join(platform_list)}

## 🎯 Top Messaging Hooks (From Live Ads)
{chr(10).join(f"• \"{h[:80]}{'...' if len(h) > 80 else ''}\"" for h in headlines[:5])}

## 🎨 Creative Strategy Intelligence  
- **Media Format Distribution**: {media_types['image']} images, {media_types['video']} videos, {media_types['text_only']} text-only
- **Dominant Format**: {dominant_media.title()} ({max(media_types.values()) if media_types.values() else 0} ads)
- **Primary CTA**: "{dominant_cta}"
- **CTA Variety**: {len(set(cta_types))} different CTAs tested

## 📈 Messaging Theme Analysis
- **Scientific Authority**: {"✅ Heavy clinical validation focus" if themes['science'] else "⚠️ Limited scientific claims"}
- **Convenience Positioning**: {"✅ Simplicity messaging dominates" if themes['convenience'] else "⚠️ Complex positioning approach"}
- **Energy/Performance**: {"✅ Performance benefits highlighted" if themes['energy'] else "⚠️ Limited energy claims"}
- **Health Focus**: {"✅ Wellness-centered messaging" if themes['health'] else "⚠️ Non-health positioning"}

## 🎯 Strategic Opportunities 
1. **Creative Format Gap**: {f"They're underutilizing {min(media_types, key=media_types.get)} format" if any(media_types.values()) else "Mixed format strategy"}
2. **Platform Expansion**: {f"Missing opportunities on {len(['INSTAGRAM', 'AUDIENCE_NETWORK', 'MESSENGER', 'THREADS']) - len(platforms_used)} platforms" if len(platforms_used) < 4 else "Full platform coverage"}
3. **CTA Optimization**: Test alternatives to their dominant "{dominant_cta}" CTA
4. **Landing Page Testing**: {len(landing_pages)} pages suggests {"extensive" if len(landing_pages) > 3 else "limited"} funnel testing

## 💡 Immediate Counter-Tactics
- **Creative Differentiation**: Focus on {min(media_types, key=media_types.get) if any(media_types.values()) else "video"} ads to differentiate
- **Platform Strategy**: {"Expand beyond their limited platform mix" if len(platforms_used) < 3 else "Match their cross-platform approach"}
- **CTA Testing**: A/B test alternative CTAs vs their "{dominant_cta}"
- **Messaging Angle**: Exploit gaps in their {min(themes, key=lambda x: themes[x]) if themes else "messaging"} positioning

## 📊 Campaign Velocity Analysis
- **Total Ad Volume**: {len(ads)} suggests {"aggressive" if len(ads) > 10 else "moderate" if len(ads) > 5 else "conservative"} spending
- **Active Ratio**: {int(active_ads/len(ads)*100) if ads else 0}% indicates {"high velocity testing" if ads and active_ads/len(ads) > 0.7 else "selective ad rotation"}
- **Creative Diversity**: {len(headlines)} variations shows {"extensive creative testing" if len(headlines) > 8 else "focused messaging approach"}

**Live competitive intelligence from {len(ads)} real {brand_name} ads • {datetime.now().strftime("%Y-%m-%d %H:%M")}**"""
        
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
    
    def run_analysis(self, brand_filter: Optional[str] = None) -> Tuple[str, Dict]:
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
        all_insights = {}
        for brand_name, brand_config in active_brands.items():
            print(f"\n--- Analyzing {brand_name} ---")
            
            # Collect ads
            ads = self.collect_ads(brand_name, brand_config)
            total_ads += len(ads)
            
            # Analyze with Claude
            analysis, insights = self.analyze_with_claude(brand_name, ads)
            all_insights[brand_name] = insights
            
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
        
        return report, all_insights


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
        report, insights = intel.run_analysis(args.brand)
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