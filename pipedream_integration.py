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
        return f"""
import requests
import json
from datetime import datetime

# Configuration from competitive intelligence tool
API_KEYS = {{
    "apify": "{config.get('apify_key', 'USER_PROVIDED')}",
    "claude": "{config.get('claude_key', 'USER_PROVIDED')}"
}}

BRANDS = {json.dumps(config.get('brands', []))}
LOOKBACK_DAYS = {config.get('lookback_days', 7)}
MAX_ADS = {config.get('max_ads', 10)}

def run_analysis():
    # Note: This would call your competitive intelligence API
    # For now, return a placeholder response
    
    analysis_url = "{config.get('analysis_endpoint', 'https://your-competitive-intel-api.com/analyze')}"
    
    payload = {{
        "brands": BRANDS,
        "lookback_days": LOOKBACK_DAYS,
        "max_ads": MAX_ADS,
        "api_keys": API_KEYS
    }}
    
    try:
        response = requests.post(analysis_url, json=payload, timeout=300)
        if response.status_code == 200:
            return response.json()
        else:
            return {{"error": f"Analysis failed: {{response.status_code}}"}}
    except Exception as e:
        return {{"error": f"Analysis error: {{str(e)}}"}}

# Execute analysis
result = run_analysis()

# Export for next step
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
        return """🎯 **Competitive Intelligence Report**

**Analysis Date**: {{new Date().toLocaleDateString()}}
**Brands Analyzed**: {{steps.fetch_competitive_data.$return_value.brands_count || 'N/A'}}
**Total Ads Found**: {{steps.fetch_competitive_data.$return_value.total_ads || 'N/A'}}

**Key Insights**:
{{steps.fetch_competitive_data.$return_value.summary || 'Analysis in progress...'}}

**Top Findings**:
• Media Distribution: {{steps.fetch_competitive_data.$return_value.media_breakdown || 'N/A'}}
• Messaging Themes: {{steps.fetch_competitive_data.$return_value.theme_analysis || 'N/A'}}
• Platform Strategy: {{steps.fetch_competitive_data.$return_value.platform_insights || 'N/A'}}

{{steps.fetch_competitive_data.$return_value.error ? '❌ Error: ' + steps.fetch_competitive_data.$return_value.error : '✅ Analysis completed successfully'}}

📊 [View Full Report]({{steps.fetch_competitive_data.$return_value.report_url || 'N/A'}})"""
    
    def _get_discord_message_template(self) -> str:
        """Get Discord message template (similar format to Slack)"""
        return self._get_slack_message_template()
    
    def _get_teams_message_template(self) -> str:
        """Get Teams message template"""
        return """
# 🎯 Competitive Intelligence Report

**Analysis Date**: {{new Date().toLocaleDateString()}}

## Summary
- **Brands Analyzed**: {{steps.fetch_competitive_data.$return_value.brands_count || 'N/A'}}
- **Total Ads Found**: {{steps.fetch_competitive_data.$return_value.total_ads || 'N/A'}}

## Key Insights
{{steps.fetch_competitive_data.$return_value.summary || 'Analysis in progress...'}}

## Detailed Findings
- **Media Distribution**: {{steps.fetch_competitive_data.$return_value.media_breakdown || 'N/A'}}
- **Messaging Themes**: {{steps.fetch_competitive_data.$return_value.theme_analysis || 'N/A'}}
- **Platform Strategy**: {{steps.fetch_competitive_data.$return_value.platform_insights || 'N/A'}}

{{steps.fetch_competitive_data.$return_value.error ? '❌ Error: ' + steps.fetch_competitive_data.$return_value.error : '✅ Analysis completed successfully'}}
"""
    
    def _get_email_template(self) -> str:
        """Get email template"""
        return """
<h2>🎯 Competitive Intelligence Report</h2>
<p><strong>Analysis Date:</strong> {{new Date().toLocaleDateString()}}</p>

<h3>Summary</h3>
<ul>
    <li><strong>Brands Analyzed:</strong> {{steps.fetch_competitive_data.$return_value.brands_count || 'N/A'}}</li>
    <li><strong>Total Ads Found:</strong> {{steps.fetch_competitive_data.$return_value.total_ads || 'N/A'}}</li>
</ul>

<h3>Key Insights</h3>
<p>{{steps.fetch_competitive_data.$return_value.summary || 'Analysis in progress...'}}</p>

<h3>Detailed Findings</h3>
<ul>
    <li><strong>Media Distribution:</strong> {{steps.fetch_competitive_data.$return_value.media_breakdown || 'N/A'}}</li>
    <li><strong>Messaging Themes:</strong> {{steps.fetch_competitive_data.$return_value.theme_analysis || 'N/A'}}</li>
    <li><strong>Platform Strategy:</strong> {{steps.fetch_competitive_data.$return_value.platform_insights || 'N/A'}}</li>
</ul>

<p>{{steps.fetch_competitive_data.$return_value.error ? '❌ Error: ' + steps.fetch_competitive_data.$return_value.error : '✅ Analysis completed successfully'}}</p>
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