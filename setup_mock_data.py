"""Simple script to populate the database with mock data.

Run this to set up test data for development.
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
ROOT_DIR = Path(__file__).parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database import mock_data
from setup_mock_suggestions import populate_suggestions


if __name__ == "__main__":
    print("This will clear existing data and populate with mock data.")
    response = input("Continue? (y/n): ")
    
    if response.lower() == 'y':
        mock_data.clear_all_data()
        mock_data.populate_mock_data()
        populate_suggestions(user_id=1)
    else:
        print("Cancelled.")
