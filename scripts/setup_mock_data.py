"""Simple script to populate the database with mock data.

Run this to set up test data for development.
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import from root modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import mock_data

# Import from the same directory
import importlib.util
spec = importlib.util.spec_from_file_location(
    "setup_mock_suggestions",
    Path(__file__).parent / "setup_mock_suggestions.py"
)
setup_mock_suggestions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup_mock_suggestions)
populate_suggestions = setup_mock_suggestions.populate_suggestions


if __name__ == "__main__":
    print("This will clear existing data and populate with mock data.")
    response = input("Continue? (y/n): ")
    
    if response.lower() == 'y':
        mock_data.clear_all_data()
        mock_data.populate_mock_data()
        populate_suggestions(user_id=1)
    else:
        print("Cancelled.")
