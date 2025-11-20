"""
Main entry points for the Crypto Outlier Detection Dashboard.

Entry points:
    - update_universe: Update the universe of top 50 assets
    - run_hourly: Run the hourly ETL pipeline
    - serve_dashboard: Start the dashboard server
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cli import main

if __name__ == "__main__":
    main()
