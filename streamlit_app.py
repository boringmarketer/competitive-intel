import streamlit as st
import json
import os
from datetime import datetime
from main import CompetitiveIntel
import glob
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import Dict, Any

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
        # Convert secrets to a regular dict to avoid read-only issues
        config = {}
        for key in st.secrets.config:
            config[key] = dict(st.secrets.config[key])
        return config
    
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

def get_session_config(base_config):
    """Get configuration with session-based API keys if available"""
    config = dict(base_config)
    
    # Override with session keys if available
    if 'temp_apify_key' in st.session_state and st.session_state.temp_apify_key:
        config['apify'] = {'api_token': st.session_state.temp_apify_key}
    if 'temp_claude_key' in st.session_state and st.session_state.temp_claude_key:
        config['claude'] = {'api_key': st.session_state.temp_claude_key}
    
    return config

def create_media_distribution_chart(insights: Dict) -> go.Figure:
    """Create media distribution pie chart"""
    media_data = insights.get('media_distribution', {})
    if not any(media_data.values()):
        return None
    
    fig = px.pie(
        values=list(media_data.values()),
        names=list(media_data.keys()),
        title="📱 Media Format Distribution",
        color_discrete_map={
            'video': '#FF6B6B',
            'image': '#4ECDC4', 
            'text_only': '#45B7D1'
        }
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    return fig

def create_theme_analysis_chart(insights: Dict) -> go.Figure:
    """Create theme analysis bar chart"""
    themes = insights.get('themes', {})
    if not any(themes.values()):
        return None
    
    # Filter out zero values and sort by count
    filtered_themes = {k: v for k, v in themes.items() if v > 0}
    if not filtered_themes:
        return None
    
    sorted_themes = dict(sorted(filtered_themes.items(), key=lambda x: x[1], reverse=True))
    
    fig = px.bar(
        x=list(sorted_themes.values()),
        y=list(sorted_themes.keys()),
        orientation='h',
        title="🎯 Messaging Themes Distribution",
        labels={'x': 'Number of Ads', 'y': 'Theme'},
        color=list(sorted_themes.values()),
        color_continuous_scale='Viridis'
    )
    fig.update_layout(showlegend=False)
    return fig

def create_platform_distribution_chart(insights: Dict) -> go.Figure:
    """Create platform distribution chart"""
    platforms = insights.get('platform_distribution', {})
    if not any(platforms.values()):
        return None
    
    fig = px.bar(
        x=list(platforms.keys()),
        y=list(platforms.values()),
        title="📊 Platform Distribution",
        labels={'x': 'Platform', 'y': 'Number of Ads'},
        color=list(platforms.values()),
        color_continuous_scale='Blues'
    )
    return fig

def create_cta_analysis_chart(insights: Dict) -> go.Figure:
    """Create CTA analysis chart"""
    ctas = insights.get('cta_types', {})
    if not any(ctas.values()):
        return None
    
    # Get top 10 CTAs
    sorted_ctas = dict(sorted(ctas.items(), key=lambda x: x[1], reverse=True)[:10])
    
    fig = px.bar(
        x=list(sorted_ctas.values()),
        y=list(sorted_ctas.keys()),
        orientation='h',
        title="💬 Top Call-to-Action Types",
        labels={'x': 'Frequency', 'y': 'CTA Text'},
        color=list(sorted_ctas.values()),
        color_continuous_scale='Oranges'
    )
    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
    return fig

def show_insights_dashboard(insights: Dict[str, Dict]):
    """Show interactive insights dashboard"""
    st.markdown("## 📊 Visual Insights Dashboard")
    
    if not insights:
        st.info("Run an analysis to see visual insights!")
        return
    
    # Aggregate insights across all brands
    total_media = {"video": 0, "image": 0, "text_only": 0}
    total_themes = {"science": 0, "convenience": 0, "energy": 0, "health": 0, "premium": 0, "social_proof": 0, "urgency": 0}
    total_platforms = {}
    total_ctas = {}
    total_performance = {"total_ads": 0, "active_ads": 0, "unique_headlines": 0, "unique_landing_pages": 0}
    
    for brand_name, brand_insights in insights.items():
        # Aggregate media distribution
        for media_type, count in brand_insights.get('media_distribution', {}).items():
            total_media[media_type] += count
        
        # Aggregate themes
        for theme, count in brand_insights.get('themes', {}).items():
            total_themes[theme] += count
        
        # Aggregate platforms
        for platform, count in brand_insights.get('platform_distribution', {}).items():
            total_platforms[platform] = total_platforms.get(platform, 0) + count
        
        # Aggregate CTAs
        for cta, count in brand_insights.get('cta_types', {}).items():
            total_ctas[cta] = total_ctas.get(cta, 0) + count
        
        # Aggregate performance
        perf = brand_insights.get('performance_indicators', {})
        total_performance['total_ads'] += perf.get('total_ads', 0)
        total_performance['active_ads'] += perf.get('active_ads', 0)
        total_performance['unique_headlines'] += perf.get('unique_headlines', 0)
        total_performance['unique_landing_pages'] += perf.get('unique_landing_pages', 0)
    
    # Create aggregated insights for charts
    aggregated_insights = {
        'media_distribution': total_media,
        'themes': total_themes,
        'platform_distribution': total_platforms,
        'cta_types': total_ctas,
        'performance_indicators': total_performance
    }
    
    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Ads Analyzed", total_performance['total_ads'])
    with col2:
        active_rate = int(total_performance['active_ads'] / total_performance['total_ads'] * 100) if total_performance['total_ads'] > 0 else 0
        st.metric("Active Rate", f"{active_rate}%")
    with col3:
        st.metric("Unique Headlines", total_performance['unique_headlines'])
    with col4:
        st.metric("Unique Landing Pages", total_performance['unique_landing_pages'])
    
    # Create charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Media distribution chart
        media_fig = create_media_distribution_chart(aggregated_insights)
        if media_fig:
            st.plotly_chart(media_fig, use_container_width=True)
        
        # Platform distribution chart
        platform_fig = create_platform_distribution_chart(aggregated_insights)
        if platform_fig:
            st.plotly_chart(platform_fig, use_container_width=True)
    
    with col2:
        # Theme analysis chart
        theme_fig = create_theme_analysis_chart(aggregated_insights)
        if theme_fig:
            st.plotly_chart(theme_fig, use_container_width=True)
        
        # CTA analysis chart
        cta_fig = create_cta_analysis_chart(aggregated_insights)
        if cta_fig:
            st.plotly_chart(cta_fig, use_container_width=True)
    
    # Brand-by-brand breakdown
    if len(insights) > 1:
        st.markdown("### 🏢 Brand-by-Brand Breakdown")
        
        for brand_name, brand_insights in insights.items():
            with st.expander(f"📊 {brand_name} Detailed Insights"):
                perf = brand_insights.get('performance_indicators', {})
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(f"{brand_name} Total Ads", perf.get('total_ads', 0))
                with col2:
                    st.metric(f"{brand_name} Active Ads", perf.get('active_ads', 0))
                with col3:
                    avg_days = perf.get('avg_days_running', 0)
                    st.metric(f"Avg Days Running", f"{avg_days} days")
                
                # Individual brand charts
                brand_col1, brand_col2 = st.columns(2)
                
                with brand_col1:
                    brand_media_fig = create_media_distribution_chart(brand_insights)
                    if brand_media_fig:
                        brand_media_fig.update_layout(title=f"{brand_name} - Media Distribution")
                        st.plotly_chart(brand_media_fig, use_container_width=True)
                
                with brand_col2:
                    brand_theme_fig = create_theme_analysis_chart(brand_insights)
                    if brand_theme_fig:
                        brand_theme_fig.update_layout(title=f"{brand_name} - Messaging Themes")
                        st.plotly_chart(brand_theme_fig, use_container_width=True)

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
    
    # Check if user has completed setup steps
    has_api_keys = ('temp_apify_key' in st.session_state and st.session_state.temp_apify_key) and \
                   ('temp_claude_key' in st.session_state and st.session_state.temp_claude_key)
    has_brands = ('selected_brands' in st.session_state and st.session_state.selected_brands) or \
                 ('quick_brands' in st.session_state and st.session_state.quick_brands)
    
    # Sidebar for navigation with step progress
    st.sidebar.title("🎯 Competitive Intel")
    
    # Progress indicator
    st.sidebar.markdown("### Setup Progress")
    step1_status = "✅" if has_api_keys else "1️⃣"
    step2_status = "✅" if has_brands else "2️⃣" if has_api_keys else "⏸️"
    step3_status = "✅" if has_api_keys and has_brands else "3️⃣" if has_api_keys and has_brands else "⏸️"
    
    st.sidebar.markdown(f"""
    {step1_status} **Step 1**: API Keys  
    {step2_status} **Step 2**: Select Brands  
    {step3_status} **Step 3**: Run Analysis  
    """)
    
    # Navigation based on setup status
    if not has_api_keys:
        # Force to Step 1 if no API keys
        available_pages = ["1️⃣ Step 1: Enter API Keys"]
        default_page = "1️⃣ Step 1: Enter API Keys"
    elif not has_brands:
        # Step 1 complete, show Step 2
        available_pages = [
            "1️⃣ Step 1: Enter API Keys",
            "2️⃣ Step 2: Select Brands"
        ]
        default_page = "2️⃣ Step 2: Select Brands"
    else:
        # All steps available
        available_pages = [
            "1️⃣ Step 1: Enter API Keys",
            "2️⃣ Step 2: Select Brands", 
            "3️⃣ Step 3: Run Analysis",
            "📈 Visual Insights",
            "📄 View Reports"
        ]
        default_page = "3️⃣ Step 3: Run Analysis"
    
    # Add advanced options for experienced users
    st.sidebar.markdown("---")
    show_advanced = st.sidebar.checkbox("🔧 Show All Pages", help="Access all features directly")
    
    if show_advanced:
        available_pages = [
            "1️⃣ Step 1: Enter API Keys",
            "2️⃣ Step 2: Select Brands", 
            "3️⃣ Step 3: Run Analysis",
            "🎯 Brand Management", 
            "📈 Visual Insights",
            "📄 View Reports"
        ]
    
    page = st.sidebar.selectbox("Choose a page", available_pages, 
                               index=0 if not show_advanced else available_pages.index(default_page) if default_page in available_pages else 0)
    
    if page == "1️⃣ Step 1: Enter API Keys":
        show_step1_api_keys()
    elif page == "2️⃣ Step 2: Select Brands":
        show_step2_brand_selection(config)
    elif page == "3️⃣ Step 3: Run Analysis":
        show_step3_run_analysis(config)
    elif page == "🎯 Brand Management":
        show_brand_management(config)
    elif page == "📈 Visual Insights":
        # Get insights from session state if available
        insights = st.session_state.get('analysis_insights', {})
        show_insights_dashboard(insights)
    elif page == "📄 View Reports":
        show_reports()

def show_step1_api_keys():
    """Step 1: API Keys Setup"""
    st.markdown("# 1️⃣ Step 1: Enter Your API Keys")
    st.markdown("---")
    
    st.markdown("""
    ### Welcome to Competitive Intelligence Tool! 🎯
    
    To get started, you'll need API keys for data collection and analysis:
    - **Apify**: Scrapes Facebook Ad Library data
    - **Claude**: Analyzes ads and provides strategic insights
    
    *Your keys are stored only for this browser session and will be cleared when you close the tab.*
    """)
    
    # API Key inputs in a cleaner layout
    st.markdown("### 🔑 Your API Keys")
    
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown("#### 🔍 Apify API Key")
        apify_key = st.text_input(
            "Enter your Apify API token",
            value=st.session_state.get('temp_apify_key', ''),
            type="password",
            placeholder="apify_api_...",
            key="step1_apify"
        )
        st.markdown("**[Get your free Apify key →](https://console.apify.com/account/integrations)**")
        st.caption("Free tier: 1,000 results/month")
        
        if apify_key:
            st.session_state.temp_apify_key = apify_key
            st.success("✅ Apify key set!")
    
    with col2:
        st.markdown("#### 🧠 Claude API Key")
        claude_key = st.text_input(
            "Enter your Claude API key",
            value=st.session_state.get('temp_claude_key', ''),
            type="password", 
            placeholder="sk-ant-...",
            key="step1_claude"
        )
        st.markdown("**[Get your Claude key →](https://console.anthropic.com)**")
        st.caption("$5 free credit for new users")
        
        if claude_key:
            st.session_state.temp_claude_key = claude_key
            st.success("✅ Claude key set!")
    
    # Progress check
    st.markdown("---")
    st.markdown("### ✅ Setup Status")
    
    has_apify = 'temp_apify_key' in st.session_state and st.session_state.temp_apify_key
    has_claude = 'temp_claude_key' in st.session_state and st.session_state.temp_claude_key
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if has_apify:
            st.success("✅ Apify Ready")
        else:
            st.error("❌ Apify Needed")
    
    with col2:
        if has_claude:
            st.success("✅ Claude Ready")
        else:
            st.error("❌ Claude Needed")
    
    with col3:
        if has_apify and has_claude:
            st.success("🎉 Ready for Step 2!")
            if st.button("➡️ Continue to Step 2: Select Brands", type="primary", use_container_width=True):
                st.rerun()
        else:
            st.warning("⏳ Complete setup above")
    
    # Help section
    if not (has_apify and has_claude):
        st.markdown("---")
        with st.expander("🆘 Need help getting API keys?"):
            st.markdown("""
            **Apify Setup:**
            1. Go to [console.apify.com](https://console.apify.com)
            2. Sign up for free account
            3. Go to Account → Integrations
            4. Copy your API token
            
            **Claude Setup:**
            1. Go to [console.anthropic.com](https://console.anthropic.com)
            2. Sign up and verify email
            3. Go to API Keys section
            4. Create new API key
            """)

def show_step2_brand_selection(config):
    """Step 2: Brand Selection"""
    st.markdown("# 2️⃣ Step 2: Select Brands to Analyze")
    st.markdown("---")
    
    st.markdown("""
    ### Choose which brands you want to analyze 🎯
    
    You can analyze pre-configured example brands or add your own custom brands.
    """)
    
    # Initialize selected brands if not exists
    if 'selected_brands' not in st.session_state:
        st.session_state.selected_brands = []
    
    # Pre-configured brands
    st.markdown("### 📋 Pre-configured Example Brands")
    st.markdown("*These brands are ready to analyze - just check the boxes!*")
    
    available_brands = config.get("brands", {})
    
    if available_brands:
        for brand_name, brand_config in available_brands.items():
            if brand_config.get("active", True):
                is_selected = st.checkbox(
                    f"**{brand_name}** - {brand_config.get('domain', 'No domain')}",
                    value=brand_name in st.session_state.selected_brands,
                    key=f"brand_select_{brand_name}"
                )
                
                if is_selected and brand_name not in st.session_state.selected_brands:
                    st.session_state.selected_brands.append(brand_name)
                elif not is_selected and brand_name in st.session_state.selected_brands:
                    st.session_state.selected_brands.remove(brand_name)
    else:
        st.info("No pre-configured brands available.")
    
    # Custom brand addition
    st.markdown("---")
    st.markdown("### ➕ Add Your Own Brand")
    
    with st.expander("Add Custom Brand"):
        col1, col2 = st.columns(2)
        
        with col1:
            custom_brand_name = st.text_input("Brand Name", placeholder="e.g., Your Competitor")
            custom_facebook_id = st.text_input("Facebook Page ID", placeholder="e.g., 123456789")
        
        with col2:
            custom_domain = st.text_input("Website Domain", placeholder="e.g., competitor.com")
            
        if st.button("➕ Add This Brand"):
            if custom_brand_name and (custom_facebook_id or custom_domain):
                # Store in session state
                if 'quick_brands' not in st.session_state:
                    st.session_state.quick_brands = {}
                
                st.session_state.quick_brands[custom_brand_name] = {
                    "facebook_id": custom_facebook_id,
                    "domain": custom_domain,
                    "active": True
                }
                
                # Add to selected brands
                if custom_brand_name not in st.session_state.selected_brands:
                    st.session_state.selected_brands.append(custom_brand_name)
                
                st.success(f"✅ Added {custom_brand_name}!")
                st.rerun()
            else:
                st.error("Please provide at least brand name and Facebook ID or domain")
    
    # Show custom brands if any
    if 'quick_brands' in st.session_state and st.session_state.quick_brands:
        st.markdown("#### Your Custom Brands:")
        for brand_name, brand_config in st.session_state.quick_brands.items():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"🏢 **{brand_name}** - {brand_config.get('domain', 'No domain')}")
            with col2:
                if st.button("🗑️", key=f"delete_{brand_name}", help="Remove brand"):
                    del st.session_state.quick_brands[brand_name]
                    if brand_name in st.session_state.selected_brands:
                        st.session_state.selected_brands.remove(brand_name)
                    st.rerun()
    
    # Selection summary and continue
    st.markdown("---")
    st.markdown("### 📊 Analysis Selection")
    
    total_selected = len(st.session_state.selected_brands)
    
    if total_selected > 0:
        st.success(f"✅ **{total_selected} brand(s) selected for analysis:**")
        for brand in st.session_state.selected_brands:
            st.write(f"• {brand}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Back to Step 1", use_container_width=True):
                st.rerun()
        with col2:
            if st.button("➡️ Continue to Step 3: Run Analysis", type="primary", use_container_width=True):
                st.rerun()
    else:
        st.warning("⚠️ Please select at least one brand to analyze")
        if st.button("⬅️ Back to Step 1", use_container_width=True):
            st.rerun()

def show_step3_run_analysis(config):
    """Step 3: Run Analysis"""
    st.markdown("# 3️⃣ Step 3: Run Analysis")
    st.markdown("---")
    
    # Get session-enhanced config
    session_config = get_session_config(config)
    
    # Add selected brands to config
    if 'selected_brands' in st.session_state:
        # Filter brands based on selection
        selected_brand_configs = {}
        
        # Add selected pre-configured brands
        for brand_name in st.session_state.selected_brands:
            if brand_name in config.get("brands", {}):
                selected_brand_configs[brand_name] = config["brands"][brand_name]
        
        # Add selected custom brands
        if 'quick_brands' in st.session_state:
            for brand_name in st.session_state.selected_brands:
                if brand_name in st.session_state.quick_brands:
                    selected_brand_configs[brand_name] = st.session_state.quick_brands[brand_name]
        
        session_config['brands'] = selected_brand_configs
    
    # Analysis summary
    st.markdown("### 🎯 Analysis Summary")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        total_brands = len(st.session_state.get('selected_brands', []))
        st.metric("Brands to Analyze", total_brands)
    
    with col2:
        st.metric("Max Ads per Brand", session_config.get('analysis', {}).get('max_ads_per_brand', 10))
    
    with col3:
        st.metric("Lookback Days", session_config.get('analysis', {}).get('lookback_days', 7))
    
    # Show selected brands
    if st.session_state.get('selected_brands'):
        st.markdown("**Selected Brands:**")
        for brand in st.session_state.selected_brands:
            st.write(f"• {brand}")
    else:
        st.error("❌ No brands selected. Go back to Step 2.")
        if st.button("⬅️ Back to Step 2"):
            st.rerun()
        return
    
    # Analysis options
    st.markdown("---")
    st.markdown("### ⚙️ Analysis Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        analyze_all = st.radio(
            "Analysis Scope",
            ["All selected brands", "Single brand only"],
            help="Choose whether to analyze all brands or focus on one"
        )
        
        if analyze_all == "Single brand only":
            single_brand = st.selectbox("Choose brand", st.session_state.selected_brands)
        else:
            single_brand = None
    
    with col2:
        include_notifications = st.checkbox(
            "Send Notifications",
            value=False,
            help="Send results via webhook (if configured)"
        )
    
    # Run analysis button
    st.markdown("---")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("⬅️ Back to Step 2", use_container_width=True):
            st.rerun()
    
    with col2:
        if st.button("🚀 Run Competitive Analysis", type="primary", use_container_width=True):
            if "analysis_running" not in st.session_state:
                st.session_state.analysis_running = False
            
            if not st.session_state.analysis_running:
                st.session_state.analysis_running = True
                
                with st.spinner("🔄 Running competitive intelligence analysis..."):
                    try:
                        # Initialize tool with session config
                        intel = CompetitiveIntel()
                        intel.config = session_config
                        
                        # Override notification setting
                        intel.config["notifications"]["enabled"] = include_notifications
                        
                        # Run analysis
                        brand_to_analyze = single_brand if analyze_all == "Single brand only" else None
                        
                        st.info("🔄 Starting analysis... This may take 1-2 minutes per brand.")
                        report, insights = intel.run_analysis(brand_to_analyze)
                        
                        if report and insights:
                            st.success("✅ Analysis completed successfully!")
                            
                            # Store insights for visual dashboard
                            st.session_state.analysis_insights = insights
                            
                            # Show key metrics
                            total_ads = sum(brand_insights.get('performance_indicators', {}).get('total_ads', 0) 
                                          for brand_insights in insights.values())
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Total Ads Found", total_ads)
                            with col2:
                                st.metric("Brands Analyzed", len(insights))
                            with col3:
                                active_ads = sum(brand_insights.get('performance_indicators', {}).get('active_ads', 0) 
                                               for brand_insights in insights.values())
                                st.metric("Active Ads", active_ads)
                            
                            # Action buttons
                            st.markdown("### 🎉 Analysis Complete! What's next?")
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.download_button(
                                    "📥 Download Report",
                                    data=report,
                                    file_name=f"competitive_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                                    mime="text/markdown",
                                    use_container_width=True
                                )
                            
                            with col2:
                                if st.button("📊 View Visual Insights", use_container_width=True):
                                    st.session_state.goto_insights = True
                                    st.rerun()
                            
                            with col3:
                                if st.button("🔄 Analyze Different Brands", use_container_width=True):
                                    # Reset selections for new analysis
                                    st.session_state.selected_brands = []
                                    if 'quick_brands' in st.session_state:
                                        del st.session_state.quick_brands
                                    st.rerun()
                            
                            # Show report preview
                            st.markdown("---")
                            st.markdown("### 📄 Report Preview")
                            st.markdown(report[:1000] + "..." if len(report) > 1000 else report)
                            
                        else:
                            st.error("❌ Analysis failed. Please check your API keys and try again.")
                    
                    except Exception as e:
                        st.error(f"❌ Analysis error: {str(e)}")
                        st.markdown("**Common issues:**")
                        st.markdown("- Invalid API keys")
                        st.markdown("- Insufficient API credits")
                        st.markdown("- Network connectivity issues")
                    
                    finally:
                        st.session_state.analysis_running = False

def show_quick_setup():
    """Quick setup page for session-based API keys"""
    st.markdown('<h2 class="section-header">🔑 Quick Setup - Enter Your API Keys</h2>', unsafe_allow_html=True)
    
    st.markdown("""
    **New to the tool?** Enter your API keys below to get started immediately. 
    Your keys are only stored for this session and will be cleared when you close your browser.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔍 Apify API Key")
        temp_apify_key = st.text_input(
            "Apify API Token",
            value=st.session_state.get('temp_apify_key', ''),
            type="password",
            help="Get your token from console.apify.com/account/integrations",
            key="apify_input"
        )
        st.markdown("[Get Apify API Key →](https://console.apify.com/account/integrations)")
        
        if temp_apify_key:
            st.session_state.temp_apify_key = temp_apify_key
            st.success("✅ Apify API key set for this session")
    
    with col2:
        st.markdown("### 🧠 Claude API Key")
        temp_claude_key = st.text_input(
            "Claude API Key",
            value=st.session_state.get('temp_claude_key', ''),
            type="password",
            help="Get your key from console.anthropic.com",
            key="claude_input"
        )
        st.markdown("[Get Claude API Key →](https://console.anthropic.com)")
        
        if temp_claude_key:
            st.session_state.temp_claude_key = temp_claude_key
            st.success("✅ Claude API key set for this session")
    
    # Quick brand setup
    st.markdown("### 🎯 Quick Brand Setup")
    st.markdown("Add a brand to analyze (you can add more in Brand Management):")
    
    col1, col2 = st.columns(2)
    with col1:
        quick_brand_name = st.text_input("Brand Name", placeholder="e.g., Athletic Greens")
        quick_facebook_id = st.text_input("Facebook Page ID", placeholder="e.g., 183869772601")
    
    with col2:
        quick_domain = st.text_input("Company Domain", placeholder="e.g., drinkag1.com") 
        if st.button("➕ Add Quick Brand"):
            if quick_brand_name and (quick_facebook_id or quick_domain):
                # Store in session state
                if 'quick_brands' not in st.session_state:
                    st.session_state.quick_brands = {}
                
                st.session_state.quick_brands[quick_brand_name] = {
                    "facebook_id": quick_facebook_id,
                    "domain": quick_domain,
                    "active": True
                }
                st.success(f"✅ Added {quick_brand_name} for this session")
                st.rerun()
    
    # Show session brands
    if 'quick_brands' in st.session_state and st.session_state.quick_brands:
        st.markdown("#### Session Brands:")
        for brand_name, brand_config in st.session_state.quick_brands.items():
            st.write(f"🏢 **{brand_name}** - {brand_config.get('domain', 'No domain')}")
    
    # Status check
    st.markdown("### ✅ Setup Status")
    
    has_apify = 'temp_apify_key' in st.session_state and st.session_state.temp_apify_key
    has_claude = 'temp_claude_key' in st.session_state and st.session_state.temp_claude_key
    has_brands = 'quick_brands' in st.session_state and st.session_state.quick_brands
    
    if has_apify:
        st.success("✅ Apify API key configured")
    else:
        st.error("❌ Apify API key needed")
    
    if has_claude:
        st.success("✅ Claude API key configured")  
    else:
        st.error("❌ Claude API key needed")
    
    if has_brands:
        st.success(f"✅ {len(st.session_state.quick_brands)} brand(s) configured")
    else:
        st.warning("⚠️ No brands configured yet")
    
    if has_apify and has_claude and has_brands:
        st.success("🎉 **Ready to run analysis!** Go to 'Run Analysis' page.")
        if st.button("🚀 Go to Analysis Page"):
            st.session_state.page_redirect = "📊 Run Analysis"
            st.rerun()

def show_dashboard(config):
    """Dashboard overview"""
    st.markdown('<h2 class="section-header">🎯 Competitive Intelligence Tool</h2>', unsafe_allow_html=True)
    
    # Multi-user info
    if is_using_secrets():
        st.info("👥 **Multi-User Mode**: This is a shared tool. Use '🔑 Quick Setup' to enter your own API keys and analyze any brands you want!")
    
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
    
    # Check session vs default config
    has_session_keys = ('temp_apify_key' in st.session_state and st.session_state.temp_apify_key) or \
                      ('temp_claude_key' in st.session_state and st.session_state.temp_claude_key)
    
    if has_session_keys:
        st.success("🔑 **Using your personal API keys** (session-based)")
        if 'temp_apify_key' in st.session_state and st.session_state.temp_apify_key:
            st.write("✅ Your Apify API configured")
        if 'temp_claude_key' in st.session_state and st.session_state.temp_claude_key:
            st.write("✅ Your Claude API configured")
    else:
        st.warning("⚠️ **No personal API keys set** - You'll need your own keys to run analysis")
        st.markdown("Go to '🔑 Quick Setup' to enter your API keys")
    
    # Show session brands if any
    if 'quick_brands' in st.session_state and st.session_state.quick_brands:
        st.markdown("### 🎯 Your Session Brands")
        for brand_name in st.session_state.quick_brands:
            st.write(f"• {brand_name}")
    
    # Default brands summary
    st.markdown('<h3 class="section-header">📋 Example Brands (Available for Analysis)</h3>', unsafe_allow_html=True)
    st.markdown("*These are pre-configured brands that anyone can analyze with their own API keys*")
    
    for brand_name, brand_config in config.get("brands", {}).items():
        if brand_config.get("active", True):
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                st.write(f"**{brand_name}**")
            with col2:
                st.write(f"Domain: {brand_config.get('domain', 'N/A')}")
            with col3:
                st.write("🟢 Available")

def show_brand_management(config):
    """Brand management interface"""
    st.markdown('<h2 class="section-header">🎯 Brand Management</h2>', unsafe_allow_html=True)
    
    # Disable brand management on Streamlit Cloud to avoid config modification errors
    if is_using_secrets():
        st.info("🔒 **Brand management is disabled on Streamlit Cloud**")
        st.markdown("Brands are configured in your secrets.toml file. To add/edit brands:")
        st.code("""[config.brands.YourBrand]
facebook_id = "123456789"
domain = "yourbrand.com"
active = true""")
        st.markdown("Current brands from secrets:")
        for brand_name, brand_config in config.get("brands", {}).items():
            status = "🟢 Active" if brand_config.get("active") else "🔴 Inactive"
            st.write(f"**{brand_name}** - {status}")
        return
    
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
            if is_using_secrets():
                st.warning("⚠️ Running on Streamlit Cloud - can't save brands. Update secrets.toml manually.")
            else:
                # Create new config with added brand
                new_config = dict(config)
                new_config["brands"] = dict(config.get("brands", {}))
                new_config["brands"][new_brand_name] = {
                    "facebook_id": new_facebook_id,
                    "domain": new_domain,
                    "active": new_active
                }
                if save_config(new_config):
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
                        if is_using_secrets():
                            st.warning("⚠️ Running on Streamlit Cloud - can't save brands. Update secrets.toml manually.")
                        else:
                            # Create new config with updated brand
                            new_config = dict(config)
                            new_config["brands"] = dict(config.get("brands", {}))
                            new_config["brands"][brand_name] = {
                                "facebook_id": facebook_id,
                                "domain": domain,
                                "active": active
                            }
                            if save_config(new_config):
                                st.success(f"✅ Updated {brand_name}")
                                st.rerun()
                
                with col_delete:
                    if st.button("🗑️ Delete", key=f"delete_{brand_name}"):
                        if is_using_secrets():
                            st.warning("⚠️ Running on Streamlit Cloud - can't delete brands. Update secrets.toml manually.")
                        else:
                            # Create new config without this brand
                            new_config = dict(config)
                            new_config["brands"] = dict(config.get("brands", {}))
                            del new_config["brands"][brand_name]
                            if save_config(new_config):
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
    
    # Get session-enhanced config
    session_config = get_session_config(config)
    
    # Check if using session brands
    if 'quick_brands' in st.session_state and st.session_state.quick_brands:
        session_config['brands'] = {**session_config.get('brands', {}), **st.session_state.quick_brands}
    
    # Check configuration
    missing_config = []
    if not session_config.get("apify", {}).get("api_token"):
        missing_config.append("Apify API token")
    if not session_config.get("claude", {}).get("api_key"):
        missing_config.append("Claude API key")
    
    if missing_config:
        st.error(f"❌ Missing configuration: {', '.join(missing_config)}")
        st.markdown("### Quick Fix Options:")
        st.markdown("1. **New users**: Go to '🔑 Quick Setup' to enter your API keys")
        st.markdown("2. **Existing users**: Configure keys in 'Settings' page")
        return
    
    # Analysis options
    st.markdown("### Analysis Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        active_brands = [name for name, conf in session_config.get("brands", {}).items() if conf.get("active", True)]
        
        if not active_brands:
            st.error("❌ No active brands configured.")
            st.markdown("**Add brands via:**")
            st.markdown("- '🔑 Quick Setup' for temporary brands")
            st.markdown("- 'Brand Management' for permanent brands")
            return
        
        brand_filter = st.selectbox(
            "Select Brand",
            ["All Active Brands"] + active_brands,
            help="Choose specific brand or analyze all active brands"
        )
    
    with col2:
        include_notifications = st.checkbox(
            "Send Notifications",
            value=session_config.get("notifications", {}).get("enabled", False),
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
                    # Initialize tool with session config
                    intel = CompetitiveIntel()
                    intel.config = session_config
                    
                    # Override notification setting if disabled
                    if not include_notifications:
                        intel.config["notifications"]["enabled"] = False
                    
                    # Run analysis
                    brand_to_analyze = None if brand_filter == "All Active Brands" else brand_filter
                    
                    # Capture progress
                    progress_container = st.empty()
                    
                    with progress_container.container():
                        st.info("🔄 Starting analysis...")
                        report, insights = intel.run_analysis(brand_to_analyze)
                    
                    if report:
                        st.success("✅ Analysis completed successfully!")
                        
                        # Store insights in session state for visual dashboard
                        st.session_state.analysis_insights = insights
                        
                        # Show summary metrics
                        total_ads = sum(brand_insights.get('performance_indicators', {}).get('total_ads', 0) 
                                      for brand_insights in insights.values())
                        st.metric("Total Ads Analyzed", total_ads)
                        
                        # Show report preview
                        st.markdown("### 📄 Report Preview")
                        st.markdown(report[:1000] + "..." if len(report) > 1000 else report)
                        
                        # Action buttons
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.download_button(
                                "📥 Download Full Report",
                                data=report,
                                file_name=f"competitive_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                                mime="text/markdown"
                            )
                        with col2:
                            if st.button("📈 View Visual Insights"):
                                st.session_state.page_redirect = "📈 Visual Insights"
                                st.rerun()
                        with col3:
                            if insights:
                                st.success(f"📊 {len(insights)} brands analyzed")
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