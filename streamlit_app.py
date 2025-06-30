import streamlit as st
import json
import os
from datetime import datetime
from main import CompetitiveIntel
import glob

# Page config
st.set_page_config(
    page_title="Competitive Intelligence Tool",
    page_icon="🎯",
    layout="wide"
)

# Load CSS for better styling
st.markdown("""
<style>
.main-header {
    font-size: 2.5rem;
    font-weight: 700;
    margin-bottom: 1rem;
}
.section-header {
    font-size: 1.5rem;
    font-weight: 600;
    margin-top: 2rem;
    margin-bottom: 1rem;
}
.brand-card {
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 1rem;
    margin: 0.5rem 0;
    background-color: #f9f9f9;
}
.success-box {
    background-color: #d4edda;
    border: 1px solid #c3e6cb;
    color: #155724;
    padding: 1rem;
    border-radius: 4px;
    margin: 1rem 0;
}
.warning-box {
    background-color: #fff3cd;
    border: 1px solid #ffeaa7;
    color: #856404;
    padding: 1rem;
    border-radius: 4px;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)

def load_config():
    """Load configuration from file or Streamlit secrets"""
    # Try Streamlit secrets first (for cloud deployment)
    if hasattr(st, 'secrets') and 'config' in st.secrets:
        return dict(st.secrets.config)
    
    # Fall back to local config file
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        # Create default config for first run
        default_config = {
            "apify": {"api_token": ""},
            "claude": {"api_key": ""},
            "brands": {
                "AG1": {
                    "facebook_id": "183869772601",
                    "domain": "drinkag1.com",
                    "active": False
                }
            },
            "analysis": {"lookback_days": 7, "max_ads_per_brand": 10},
            "notifications": {"webhook_url": "", "enabled": True}
        }
        return default_config

def save_config(config):
    """Save configuration to file"""
    # For cloud deployment, show a warning about persistence
    if hasattr(st, 'secrets') and 'config' in st.secrets:
        st.warning("⚠️ Running on Streamlit Cloud - changes won't persist. Use secrets.toml for permanent config.")
        return False
    
    try:
        with open("config.json", "w") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Failed to save config: {str(e)}")
        return False

def is_using_secrets():
    """Check if we're using Streamlit secrets"""
    return hasattr(st, 'secrets') and 'config' in st.secrets

def get_recent_reports():
    """Get list of recent reports"""
    try:
        reports = glob.glob("reports/*.md")
        reports.sort(key=os.path.getmtime, reverse=True)
        return reports[:10]  # Return 10 most recent
    except:
        return []

def main():
    st.markdown('<h1 class="main-header">🎯 Competitive Intelligence Tool</h1>', unsafe_allow_html=True)
    
    # Load config
    config = load_config()
    if not config:
        return
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Choose a page", [
        "🏠 Dashboard", 
        "🎯 Brand Management", 
        "⚙️ Settings", 
        "📊 Run Analysis",
        "📄 View Reports"
    ])
    
    if page == "🏠 Dashboard":
        show_dashboard(config)
    elif page == "🎯 Brand Management":
        show_brand_management(config)
    elif page == "⚙️ Settings":
        show_settings(config)
    elif page == "📊 Run Analysis":
        show_run_analysis(config)
    elif page == "📄 View Reports":
        show_reports()

def show_dashboard(config):
    """Dashboard overview"""
    st.markdown('<h2 class="section-header">Dashboard Overview</h2>', unsafe_allow_html=True)
    
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    
    active_brands = sum(1 for brand in config["brands"].values() if brand.get("active", True))
    total_brands = len(config["brands"])
    
    with col1:
        st.metric("Active Brands", active_brands)
    
    with col2:
        st.metric("Total Brands", total_brands)
    
    with col3:
        lookback_days = config["analysis"]["lookback_days"]
        st.metric("Lookback Days", lookback_days)
    
    with col4:
        recent_reports = get_recent_reports()
        st.metric("Recent Reports", len(recent_reports))
    
    # Configuration status
    st.markdown('<h3 class="section-header">🔧 Configuration Status</h3>', unsafe_allow_html=True)
    
    # Check API keys
    api_status = []
    if config.get("apify", {}).get("api_token"):
        api_status.append("✅ Apify API configured")
    else:
        api_status.append("❌ Apify API token missing")
    
    if config.get("claude", {}).get("api_key"):
        api_status.append("✅ Claude API configured")
    else:
        api_status.append("❌ Claude API key missing")
    
    if config.get("notifications", {}).get("webhook_url"):
        api_status.append("✅ Webhook configured")
    else:
        api_status.append("⚠️ Webhook not configured (optional)")
    
    for status in api_status:
        st.write(status)
    
    # Active brands summary
    st.markdown('<h3 class="section-header">🎯 Active Brands</h3>', unsafe_allow_html=True)
    
    for brand_name, brand_config in config["brands"].items():
        if brand_config.get("active", True):
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                st.write(f"**{brand_name}**")
            with col2:
                st.write(f"Domain: {brand_config.get('domain', 'N/A')}")
            with col3:
                st.write("🟢 Active")

def show_brand_management(config):
    """Brand management interface"""
    st.markdown('<h2 class="section-header">🎯 Brand Management</h2>', unsafe_allow_html=True)
    
    # Add new brand
    st.markdown("### Add New Brand")
    
    col1, col2 = st.columns(2)
    
    with col1:
        new_brand_name = st.text_input("Brand Name", placeholder="e.g., Athletic Greens")
        new_facebook_id = st.text_input("Facebook Page ID", placeholder="e.g., 183869772601")
    
    with col2:
        new_domain = st.text_input("Company Domain", placeholder="e.g., drinkag1.com")
        new_active = st.checkbox("Active", value=True)
    
    if st.button("➕ Add Brand"):
        if new_brand_name and (new_facebook_id or new_domain):
            config["brands"][new_brand_name] = {
                "facebook_id": new_facebook_id,
                "domain": new_domain,
                "active": new_active
            }
            if save_config(config):
                st.success(f"✅ Added brand: {new_brand_name}")
                st.rerun()
        else:
            st.error("❌ Please provide brand name and either Facebook ID or domain")
    
    # Manage existing brands
    st.markdown("### Existing Brands")
    
    if not config["brands"]:
        st.info("No brands configured yet. Add your first brand above!")
        return
    
    for brand_name, brand_config in config["brands"].items():
        with st.expander(f"🏢 {brand_name}" + (" 🟢" if brand_config.get("active") else " 🔴")):
            col1, col2 = st.columns(2)
            
            with col1:
                facebook_id = st.text_input(
                    "Facebook Page ID",
                    value=brand_config.get("facebook_id", ""),
                    key=f"fb_{brand_name}"
                )
                domain = st.text_input(
                    "Company Domain",
                    value=brand_config.get("domain", ""),
                    key=f"domain_{brand_name}"
                )
            
            with col2:
                active = st.checkbox(
                    "Active",
                    value=brand_config.get("active", True),
                    key=f"active_{brand_name}"
                )
                
                st.write("")  # Spacing
                col_update, col_delete = st.columns(2)
                
                with col_update:
                    if st.button("💾 Update", key=f"update_{brand_name}"):
                        config["brands"][brand_name] = {
                            "facebook_id": facebook_id,
                            "domain": domain,
                            "active": active
                        }
                        if save_config(config):
                            st.success(f"✅ Updated {brand_name}")
                            st.rerun()
                
                with col_delete:
                    if st.button("🗑️ Delete", key=f"delete_{brand_name}"):
                        del config["brands"][brand_name]
                        if save_config(config):
                            st.success(f"✅ Deleted {brand_name}")
                            st.rerun()

def show_settings(config):
    """Settings configuration"""
    st.markdown('<h2 class="section-header">⚙️ Settings</h2>', unsafe_allow_html=True)
    
    # API Configuration
    st.markdown("### 🔑 API Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Apify API**")
        apify_token = st.text_input(
            "API Token",
            value=config.get("apify", {}).get("api_token", ""),
            type="password",
            help="Your Apify API token for Facebook ad scraping"
        )
        st.markdown("*Get token from: [console.apify.com](https://console.apify.com/account/integrations)*")
    
    with col2:
        st.markdown("**Claude API**")
        claude_key = st.text_input(
            "API Key",
            value=config.get("claude", {}).get("api_key", ""),
            type="password",
            help="Your Anthropic Claude API key"
        )
    
    # Analysis Settings
    st.markdown("### 📊 Analysis Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        lookback_days = st.number_input(
            "Lookback Days",
            min_value=1,
            max_value=90,
            value=config.get("analysis", {}).get("lookback_days", 7),
            help="How many days back to search for new ads"
        )
    
    with col2:
        max_ads = st.number_input(
            "Max Ads per Brand",
            min_value=1,
            max_value=50,
            value=config.get("analysis", {}).get("max_ads_per_brand", 10),
            help="Maximum number of ads to analyze per brand"
        )
    
    # Notification Settings
    st.markdown("### 📱 Notifications")
    
    col1, col2 = st.columns(2)
    
    with col1:
        webhook_url = st.text_input(
            "Webhook URL",
            value=config.get("notifications", {}).get("webhook_url", ""),
            help="Pipedream webhook URL for Slack notifications"
        )
    
    with col2:
        notifications_enabled = st.checkbox(
            "Enable Notifications",
            value=config.get("notifications", {}).get("enabled", True),
            help="Send reports via webhook"
        )
    
    # Save settings
    if st.button("💾 Save Settings"):
        if is_using_secrets():
            st.warning("⚠️ Running on Streamlit Cloud - settings can't be saved locally. Update your secrets.toml instead:")
            st.code(f"""[config.apify]
api_token = "{apify_token}"

[config.claude]
api_key = "{claude_key}"

[config.analysis]
lookback_days = {lookback_days}
max_ads_per_brand = {max_ads}

[config.notifications]
webhook_url = "{webhook_url}"
enabled = {str(notifications_enabled).lower()}""")
        else:
            # Create a new config dict (don't modify the read-only one)
            new_config = {
                "apify": {"api_token": apify_token},
                "claude": {"api_key": claude_key},
                "analysis": {
                    "lookback_days": lookback_days,
                    "max_ads_per_brand": max_ads
                },
                "notifications": {
                    "webhook_url": webhook_url,
                    "enabled": notifications_enabled
                },
                "brands": config.get("brands", {})
            }
            
            if save_config(new_config):
                st.success("✅ Settings saved successfully!")
                st.rerun()
            else:
                st.error("❌ Failed to save settings")

def show_run_analysis(config):
    """Run analysis interface"""
    st.markdown('<h2 class="section-header">📊 Run Analysis</h2>', unsafe_allow_html=True)
    
    # Check configuration
    missing_config = []
    if not config.get("apify", {}).get("api_token"):
        missing_config.append("Apify API token")
    if not config.get("claude", {}).get("api_key"):
        missing_config.append("Claude API key")
    
    if missing_config:
        st.error(f"❌ Missing configuration: {', '.join(missing_config)}")
        st.info("Please configure these in the Settings page before running analysis.")
        return
    
    # Analysis options
    st.markdown("### Analysis Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        active_brands = [name for name, conf in config["brands"].items() if conf.get("active", True)]
        
        if not active_brands:
            st.error("❌ No active brands configured. Please add brands in Brand Management.")
            return
        
        brand_filter = st.selectbox(
            "Select Brand",
            ["All Active Brands"] + active_brands,
            help="Choose specific brand or analyze all active brands"
        )
    
    with col2:
        include_notifications = st.checkbox(
            "Send Notifications",
            value=config["notifications"]["enabled"],
            help="Send results via webhook to Slack"
        )
    
    # Run analysis
    if st.button("🚀 Run Analysis", type="primary"):
        if "analysis_running" not in st.session_state:
            st.session_state.analysis_running = False
        
        if not st.session_state.analysis_running:
            st.session_state.analysis_running = True
            
            with st.spinner("Running competitive intelligence analysis..."):
                try:
                    # Initialize tool
                    intel = CompetitiveIntel("config.json")
                    
                    # Override notification setting if disabled
                    if not include_notifications:
                        intel.config["notifications"]["enabled"] = False
                    
                    # Run analysis
                    brand_to_analyze = None if brand_filter == "All Active Brands" else brand_filter
                    
                    # Capture progress
                    progress_container = st.empty()
                    
                    with progress_container.container():
                        st.info("🔄 Starting analysis...")
                        report = intel.run_analysis(brand_to_analyze)
                    
                    if report:
                        st.success("✅ Analysis completed successfully!")
                        
                        # Show report preview
                        st.markdown("### 📄 Report Preview")
                        st.markdown(report[:1000] + "..." if len(report) > 1000 else report)
                        
                        # Download link
                        st.download_button(
                            "📥 Download Full Report",
                            data=report,
                            file_name=f"competitive_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                            mime="text/markdown"
                        )
                    else:
                        st.error("❌ Analysis failed. Check logs for details.")
                        
                except Exception as e:
                    st.error(f"❌ Analysis error: {str(e)}")
                
                finally:
                    st.session_state.analysis_running = False

def show_reports():
    """View recent reports"""
    st.markdown('<h2 class="section-header">📄 Recent Reports</h2>', unsafe_allow_html=True)
    
    reports = get_recent_reports()
    
    if not reports:
        st.info("No reports found. Run an analysis to generate your first report!")
        return
    
    st.write(f"Found {len(reports)} recent reports:")
    
    for report_path in reports:
        filename = os.path.basename(report_path)
        file_time = datetime.fromtimestamp(os.path.getmtime(report_path))
        
        with st.expander(f"📄 {filename} - {file_time.strftime('%Y-%m-%d %H:%M')}"):
            try:
                with open(report_path, "r") as f:
                    content = f.read()
                
                # Show preview
                st.markdown(content[:500] + "..." if len(content) > 500 else content)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        "📥 Download",
                        data=content,
                        file_name=filename,
                        mime="text/markdown"
                    )
                
                with col2:
                    if st.button("👁️ View Full", key=f"view_{filename}"):
                        st.markdown("### Full Report")
                        st.markdown(content)
                        
            except Exception as e:
                st.error(f"Error reading report: {str(e)}")

if __name__ == "__main__":
    main()