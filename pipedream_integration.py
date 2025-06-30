#!/usr/bin/env python3
"""
Pipedream Integration Module
Handles OAuth authentication and workflow creation via Pipedream REST API
"""

import requests
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime

class PipedreamIntegration:
    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token
        self.base_url = "https://api.pipedream.com/v1"
        self.session = requests.Session()
        
        if api_token:
            self.session.headers.update({
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json"
            })
    
    def get_available_services(self) -> List[Dict]:
        """Get list of available services for OAuth integration"""
        # Popular services for competitive intelligence notifications
        return [
            {
                "id": "slack",
                "name": "Slack",
                "description": "Send reports to Slack channels",
                "icon": "💬",
                "oauth_required": True,
                "supported": True
            },
            {
                "id": "discord",
                "name": "Discord",
                "description": "Send reports to Discord channels",
                "icon": "🎮",
                "oauth_required": True,
                "supported": True
            },
            {
                "id": "teams",
                "name": "Microsoft Teams",
                "description": "Send reports to Teams channels",
                "icon": "🏢",
                "oauth_required": True,
                "supported": True
            },
            {
                "id": "email",
                "name": "Email",
                "description": "Send reports via email",
                "icon": "📧",
                "oauth_required": False,
                "supported": True
            },
            {
                "id": "webhook",
                "name": "Custom Webhook",
                "description": "Send to any webhook URL",
                "icon": "🔗",
                "oauth_required": False,
                "supported": True
            }
        ]
    
    def create_oauth_url(self, service: str, redirect_uri: str) -> str:
        """Generate OAuth URL for service authentication"""
        # This would need to be implemented with Pipedream's OAuth flow
        # For now, return a placeholder URL
        oauth_urls = {
            "slack": f"https://pipedream.com/connect/slack?redirect_uri={redirect_uri}",
            "discord": f"https://pipedream.com/connect/discord?redirect_uri={redirect_uri}",
            "teams": f"https://pipedream.com/connect/teams?redirect_uri={redirect_uri}"
        }
        return oauth_urls.get(service, f"https://pipedream.com/connect/{service}")
    
    def create_workflow_template(self, config: Dict) -> Dict:
        """Create a workflow template for competitive intelligence automation"""
        
        # Get service-specific configuration
        service = config.get("service", "slack")
        schedule = config.get("schedule", "daily")
        brands = config.get("brands", [])
        
        # Base workflow template
        workflow_template = {
            "name": f"Competitive Intelligence - {datetime.now().strftime('%Y-%m-%d')}",
            "description": f"Automated competitive analysis for {', '.join(brands)}",
            "triggers": [
                {
                    "type": "schedule",
                    "schedule": self._get_schedule_config(schedule),
                    "props": {}
                }
            ],
            "steps": [
                {
                    "name": "fetch_competitive_data",
                    "type": "code",
                    "props": {
                        "code": self._get_data_fetching_code(config)
                    }
                },
                {
                    "name": "send_notification",
                    "type": f"{service}_notification",
                    "props": self._get_notification_props(service, config)
                }
            ]
        }
        
        return workflow_template
    
    def _get_schedule_config(self, schedule_type: str) -> str:
        """Convert schedule type to cron expression"""
        schedules = {
            "daily": "0 9 * * *",      # 9 AM daily
            "weekly": "0 9 * * 1",     # 9 AM Mondays
            "hourly": "0 * * * *"      # Every hour
        }
        return schedules.get(schedule_type, "0 9 * * *")
    
    def _get_data_fetching_code(self, config: Dict) -> str:
        """Generate Python code for data fetching step"""
        brands_config = {}
        for brand in config.get('brands', []):
            # Use default brand configs if available
            if brand == "AG1":
                brands_config[brand] = {"facebook_id": "183869772601", "domain": "drinkag1.com", "active": True}
            else:
                brands_config[brand] = {"facebook_id": "", "domain": "", "active": True}
        
        return f"""
import requests
import json
import time
from datetime import datetime

# ⚠️ IMPORTANT: Replace these placeholder values with your actual API keys
# Go to the "Environment" tab in Pipedream and add these as environment variables:
# APIFY_API_TOKEN = "your_actual_apify_token"  
# CLAUDE_API_KEY = "your_actual_claude_key"

# Get API keys from Pipedream environment variables
import os
APIFY_TOKEN = os.environ.get('APIFY_API_TOKEN', 'REPLACE_WITH_YOUR_APIFY_TOKEN')
CLAUDE_KEY = os.environ.get('CLAUDE_API_KEY', 'REPLACE_WITH_YOUR_CLAUDE_KEY')

# Configuration from competitive intelligence tool
BRANDS_CONFIG = {json.dumps(brands_config, indent=2)}
LOOKBACK_DAYS = {config.get('lookback_days', 7)}
MAX_ADS = {config.get('max_ads', 10)}

def collect_ads_for_brand(brand_name, brand_config):
    \"\"\"Collect ads for a specific brand using Apify\"\"\"
    print(f"📊 Collecting ads for {{brand_name}}...")
    
    if not APIFY_TOKEN or APIFY_TOKEN == 'REPLACE_WITH_YOUR_APIFY_TOKEN':
        return {{"error": "Apify API token not configured"}}
    
    # Prepare Facebook page URL
    facebook_url = None
    if brand_config.get("facebook_id"):
        facebook_url = f"https://www.facebook.com/{{brand_config['facebook_id']}}"
    elif brand_config.get("domain"):
        facebook_url = f"https://www.facebook.com/{{brand_config['domain'].replace('.com', '').replace('.', '')}}"
    
    if not facebook_url:
        return {{"error": f"No Facebook URL available for {{brand_name}}"}}
    
    # Apify Actor input
    actor_input = {{
        "startUrls": [{{"url": facebook_url}}],
        "resultsLimit": MAX_ADS,
        "activeStatus": ""
    }}
    
    try:
        # Start Apify Actor
        actor_url = "https://api.apify.com/v2/acts/JJghSZmShuco4j9gJ/runs"
        headers = {{
            "Authorization": f"Bearer {{APIFY_TOKEN}}",
            "Content-Type": "application/json"
        }}
        
        response = requests.post(actor_url, json=actor_input, headers=headers, timeout=30)
        if response.status_code != 201:
            return {{"error": f"Failed to start Apify actor: {{response.status_code}}"}}
        
        run_data = response.json()
        run_id = run_data["data"]["id"]
        
        # Wait for completion (max 2 minutes)
        max_wait = 120
        wait_time = 0
        
        while wait_time < max_wait:
            status_url = f"https://api.apify.com/v2/acts/JJghSZmShuco4j9gJ/runs/{{run_id}}"
            status_response = requests.get(status_url, headers=headers, timeout=10)
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                status = status_data["data"]["status"]
                
                if status == "SUCCEEDED":
                    break
                elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                    return {{"error": f"Apify actor failed: {{status}}"}}
            
            time.sleep(10)
            wait_time += 10
        
        # Get results
        dataset_id = run_data["data"]["defaultDatasetId"]
        dataset_url = f"https://api.apify.com/v2/datasets/{{dataset_id}}/items"
        
        results_response = requests.get(dataset_url, headers=headers, timeout=30)
        if results_response.status_code == 200:
            ads = results_response.json()
            return {{"ads": ads[:MAX_ADS], "count": len(ads)}}
        else:
            return {{"error": f"Failed to get results: {{results_response.status_code}}"}}
            
    except Exception as e:
        return {{"error": f"Apify request failed: {{str(e)}}"}}

def analyze_with_claude(brand_name, ads_data):
    \"\"\"Analyze ads using Claude API\"\"\"
    if not CLAUDE_KEY or CLAUDE_KEY == 'REPLACE_WITH_YOUR_CLAUDE_KEY':
        return f"Analysis for {{brand_name}}: Claude API key not configured. Please add CLAUDE_API_KEY to environment variables."
    
    if ads_data.get("error"):
        return f"{{brand_name}} Analysis: {{ads_data['error']}}"
    
    ads = ads_data.get("ads", [])
    if not ads:
        return f"{{brand_name}}: No active ads detected. Market opportunity window identified."
    
    # Prepare ad summary for Claude
    ad_summary = []
    for i, ad in enumerate(ads[:5]):  # Analyze top 5 ads
        if "snapshot" in ad and "cards" in ad.get("snapshot", {{}}):
            snapshot = ad["snapshot"]
            cards = snapshot.get("cards", [])
            
            if cards:
                card = cards[0]
                ad_summary.append({{
                    "headline": card.get("title", "") or snapshot.get("title", ""),
                    "body_text": card.get("body", "") or snapshot.get("body", {{}}).get("text", ""),
                    "landing_page": card.get("linkUrl", "") or snapshot.get("linkUrl", ""),
                    "cta_text": card.get("ctaText", ""),
                    "media_type": "video" if (card.get("videoHdUrl") or card.get("videoSdUrl")) else "image" if card.get("originalImageUrl") else "text_only",
                    "platforms": ad.get("publisherPlatform", []),
                    "is_active": ad.get("isActive", False)
                }})
    
    prompt = f\"\"\"Analyze these {{len(ads)}} competitor ads from {{brand_name}} for strategic competitive intelligence:

{{json.dumps(ad_summary, indent=2)}}

Provide brief competitive analysis with:

## MESSAGING STRATEGY
- Key value propositions and themes
- Target audience signals
- Competitive positioning

## CREATIVE INSIGHTS  
- Media format strategy ({{len([a for a in ad_summary if a.get('media_type') == 'video'])}} videos, {{len([a for a in ad_summary if a.get('media_type') == 'image'])}} images)
- CTA patterns and optimization
- Platform distribution

## OPPORTUNITIES
- Messaging gaps to exploit
- Creative differentiators to test
- Platform expansion opportunities

## TACTICAL RECOMMENDATIONS
- 3 specific counter-messaging strategies
- 2 creative format recommendations
- 1 unique positioning angle

Keep analysis concise and actionable.\"\"\"

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={{
                "x-api-key": CLAUDE_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }},
            json={{
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 1000,
                "temperature": 0.3,
                "messages": [{{"role": "user", "content": prompt}}]
            }},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data["content"][0]["text"]
        else:
            return f"{{brand_name}} Analysis: Claude API error {{response.status_code}}"
            
    except Exception as e:
        return f"{{brand_name}} Analysis: Claude error {{str(e)}}"

# Main execution
def main():
    results = {{}}
    total_ads = 0
    
    for brand_name, brand_config in BRANDS_CONFIG.items():
        if brand_config.get("active", True):
            # Collect ads
            ads_data = collect_ads_for_brand(brand_name, brand_config)
            total_ads += ads_data.get("count", 0)
            
            # Analyze with Claude  
            analysis = analyze_with_claude(brand_name, ads_data)
            
            results[brand_name] = {{
                "ads_found": ads_data.get("count", 0),
                "analysis": analysis,
                "error": ads_data.get("error")
            }}
    
    # Generate summary report
    report_date = datetime.now().strftime("%A, %B %d, %Y")
    summary = f\"\"\"# 🎯 Competitive Intelligence Report - {{report_date}}

Generated: {{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}}
Brands Analyzed: {{len(results)}}
Total Ads Found: {{total_ads}}

\"\"\"
    
    for brand_name, data in results.items():
        summary += f\"\"\"
## {{brand_name}} Analysis
- **Ads Found**: {{data['ads_found']}}
- **Status**: {{"✅ Success" if not data.get('error') else f"❌ {{data['error']}}"}}

{{data['analysis']}}

---
\"\"\"
    
    return {{
        "summary": summary,
        "brand_results": results,
        "total_ads": total_ads,
        "brands_count": len(results),
        "timestamp": datetime.now().isoformat()
    }}

# Execute and export results
result = main()
export("analysis_result", result)
"""
    
    def _get_notification_props(self, service: str, config: Dict) -> Dict:
        """Get service-specific notification configuration"""
        
        if service == "slack":
            return {
                "channel": config.get("slack_channel", "#competitive-intel"),
                "message": self._get_slack_message_template(),
                "account": "OAUTH_ACCOUNT_ID"  # Would be replaced with actual OAuth account
            }
        elif service == "discord":
            return {
                "channel": config.get("discord_channel", "competitive-intel"),
                "message": self._get_discord_message_template(),
                "account": "OAUTH_ACCOUNT_ID"
            }
        elif service == "teams":
            return {
                "channel": config.get("teams_channel", "Competitive Intelligence"),
                "message": self._get_teams_message_template(),
                "account": "OAUTH_ACCOUNT_ID"
            }
        elif service == "email":
            return {
                "to": config.get("email_recipients", []),
                "subject": "Competitive Intelligence Report - {{new Date().toLocaleDateString()}}",
                "body": self._get_email_template()
            }
        else:
            return {
                "url": config.get("webhook_url", ""),
                "payload": "{{steps.fetch_competitive_data.$return_value}}"
            }
    
    def _get_slack_message_template(self) -> str:
        """Get Slack message template"""
        return """🎯 **Automated Competitive Intelligence Report**

**Analysis Date**: {{new Date().toLocaleDateString()}}
**Brands Analyzed**: {{steps.fetch_competitive_data.$return_value.brands_count || 'N/A'}}
**Total Ads Found**: {{steps.fetch_competitive_data.$return_value.total_ads || 'N/A'}}

**📊 Summary Report**:
```
{{steps.fetch_competitive_data.$return_value.summary || 'Analysis in progress...'}}
```

**🎯 Brand Breakdown**:
{{Object.keys(steps.fetch_competitive_data.$return_value.brand_results || {}).map(brand => `• **${brand}**: ${steps.fetch_competitive_data.$return_value.brand_results[brand].ads_found} ads found`).join('\\n') || 'No brand data available'}}

{{steps.fetch_competitive_data.$return_value.error ? '❌ Error occurred during analysis' : '✅ Automated analysis completed successfully'}}

*Generated by your automated competitive intelligence workflow*"""
    
    def _get_discord_message_template(self) -> str:
        """Get Discord message template (similar format to Slack)"""
        return self._get_slack_message_template()
    
    def _get_teams_message_template(self) -> str:
        """Get Teams message template"""
        return """
# 🎯 Automated Competitive Intelligence Report

**Analysis Date**: {{new Date().toLocaleDateString()}}

## Executive Summary
- **Brands Analyzed**: {{steps.fetch_competitive_data.$return_value.brands_count || 'N/A'}}
- **Total Ads Found**: {{steps.fetch_competitive_data.$return_value.total_ads || 'N/A'}}
- **Status**: {{steps.fetch_competitive_data.$return_value.error ? '❌ Error occurred' : '✅ Success'}}

## Detailed Analysis
{{steps.fetch_competitive_data.$return_value.summary || 'Analysis in progress...'}}

## Brand Performance
{{Object.keys(steps.fetch_competitive_data.$return_value.brand_results || {}).map(brand => `- **${brand}**: ${steps.fetch_competitive_data.$return_value.brand_results[brand].ads_found} ads analyzed`).join('\\n') || 'No brand data available'}}

*Automated competitive intelligence workflow completed at {{new Date().toLocaleTimeString()}}*
"""
    
    def _get_email_template(self) -> str:
        """Get email template"""
        return """
<h2>🎯 Automated Competitive Intelligence Report</h2>
<p><strong>Analysis Date:</strong> {{new Date().toLocaleDateString()}}</p>

<h3>Executive Summary</h3>
<ul>
    <li><strong>Brands Analyzed:</strong> {{steps.fetch_competitive_data.$return_value.brands_count || 'N/A'}}</li>
    <li><strong>Total Ads Found:</strong> {{steps.fetch_competitive_data.$return_value.total_ads || 'N/A'}}</li>
    <li><strong>Status:</strong> {{steps.fetch_competitive_data.$return_value.error ? '❌ Error occurred' : '✅ Analysis completed successfully'}}</li>
</ul>

<h3>Competitive Intelligence Report</h3>
<div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 10px 0;">
    <pre style="white-space: pre-wrap; font-family: Arial, sans-serif;">{{steps.fetch_competitive_data.$return_value.summary || 'Analysis in progress...'}}</pre>
</div>

<h3>Brand Performance Summary</h3>
<ul>
{{Object.keys(steps.fetch_competitive_data.$return_value.brand_results || {}).map(brand => `<li><strong>${brand}:</strong> ${steps.fetch_competitive_data.$return_value.brand_results[brand].ads_found} ads analyzed</li>`).join('') || '<li>No brand data available</li>'}}
</ul>

<p><em>This report was automatically generated by your competitive intelligence workflow.</em></p>
"""
    
    def create_workflow(self, template: Dict, oauth_accounts: Dict = None) -> Tuple[bool, str, Dict]:
        """Create a new workflow using the Pipedream API"""
        
        if not self.api_token:
            return False, "API token required for workflow creation", {}
        
        try:
            # Replace OAuth account placeholders with actual account IDs
            if oauth_accounts:
                template = self._replace_oauth_accounts(template, oauth_accounts)
            
            response = self.session.post(
                f"{self.base_url}/workflows",
                json={
                    "name": template["name"],
                    "description": template["description"],
                    "triggers": template["triggers"],
                    "steps": template["steps"],
                    "auto_deploy": True  # Automatically deploy the workflow
                }
            )
            
            if response.status_code == 201:
                workflow_data = response.json()
                return True, "Workflow created successfully", workflow_data
            else:
                return False, f"Failed to create workflow: {response.status_code}", {}
                
        except Exception as e:
            return False, f"Error creating workflow: {str(e)}", {}
    
    def _replace_oauth_accounts(self, template: Dict, oauth_accounts: Dict) -> Dict:
        """Replace OAuth account placeholders with actual account IDs"""
        template_str = json.dumps(template)
        
        for service, account_id in oauth_accounts.items():
            template_str = template_str.replace("OAUTH_ACCOUNT_ID", account_id)
        
        return json.loads(template_str)
    
    def get_workflow_status(self, workflow_id: str) -> Tuple[bool, Dict]:
        """Get status of a specific workflow"""
        if not self.api_token:
            return False, {"error": "API token required"}
        
        try:
            response = self.session.get(f"{self.base_url}/workflows/{workflow_id}")
            
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, {"error": f"Failed to get workflow status: {response.status_code}"}
                
        except Exception as e:
            return False, {"error": f"Error getting workflow status: {str(e)}"}
    
    def delete_workflow(self, workflow_id: str) -> Tuple[bool, str]:
        """Delete a workflow"""
        if not self.api_token:
            return False, "API token required"
        
        try:
            response = self.session.delete(f"{self.base_url}/workflows/{workflow_id}")
            
            if response.status_code == 204:
                return True, "Workflow deleted successfully"
            else:
                return False, f"Failed to delete workflow: {response.status_code}"
                
        except Exception as e:
            return False, f"Error deleting workflow: {str(e)}"

def get_oauth_instructions(service: str) -> str:
    """Get service-specific OAuth setup instructions"""
    
    instructions = {
        "slack": """
        **Slack OAuth Setup:**
        1. Go to [api.slack.com](https://api.slack.com/apps)
        2. Create a new Slack app for your workspace
        3. Add the following OAuth scopes:
           - `chat:write` (to send messages)
           - `channels:read` (to list channels)
        4. Install the app to your workspace
        5. Copy the OAuth token (starts with `xoxb-`)
        """,
        
        "discord": """
        **Discord OAuth Setup:**
        1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
        2. Create a new application
        3. Go to "Bot" section and create a bot
        4. Copy the bot token
        5. Add bot to your Discord server with appropriate permissions:
           - Send Messages
           - Read Message History
        """,
        
        "teams": """
        **Microsoft Teams Setup:**
        1. Go to [Azure Portal](https://portal.azure.com)
        2. Register a new application
        3. Configure API permissions for Microsoft Graph:
           - `ChannelMessage.Send`
           - `Team.ReadBasic.All`
        4. Generate client secret
        5. Configure webhook connector in Teams channel
        """
    }
    
    return instructions.get(service, "OAuth setup instructions not available for this service.")