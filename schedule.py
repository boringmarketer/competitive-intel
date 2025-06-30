#!/usr/bin/env python3
"""
Simple scheduler for competitive intelligence analysis
Can be used with cron or run manually
"""

import subprocess
import sys
import os
from datetime import datetime

def run_analysis():
    """Run the main analysis script"""
    print(f"🕐 Starting scheduled analysis at {datetime.now()}")
    
    try:
        # Change to script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        
        # Run main analysis
        result = subprocess.run(
            [sys.executable, "main.py"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            print("✅ Analysis completed successfully")
            print("Output:", result.stdout)
        else:
            print("❌ Analysis failed")
            print("Error:", result.stderr)
            
    except subprocess.TimeoutExpired:
        print("❌ Analysis timed out after 5 minutes")
    except Exception as e:
        print(f"❌ Scheduler error: {str(e)}")

if __name__ == "__main__":
    run_analysis()