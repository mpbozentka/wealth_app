import json
import os

DATA_FILE = "user_data.json"

DEFAULT_DATA = {
    "portfolio": [
        {"Name": "401k", "Category": "Stock Market", "Balance": 50000.0, "Monthly": 1000.0, "Rate": 0.07, "Tax Type": "Pre-Tax"},
        {"Name": "Roth IRA", "Category": "Stock Market", "Balance": 20000.0, "Monthly": 500.0, "Rate": 0.07, "Tax Type": "Roth"},
        {"Name": "Mortgage", "Category": "Debt/Liability", "Balance": 300000.0, "Monthly": 2000.0, "Rate": 0.04, "Tax Type": "N/A"}
    ],
    "events": [
        {"Event Name": "Down Payment", "Age": 35, "Cost": 50000.0}
    ],
    "settings": {
        "user_age": 30,
        "filing_status": "Single",
        "annual_spend": 60000,
        "swr": 0.04,
        "use_progressive": True,
        "tax_flat_rate": 0.15,
        "contrib_growth": 0.03,
        "inflation_rate": 0.025,
        "timeframe": "Until Age 85"
    }
}

def save_data(data):
    """Saves the data dictionary to a JSON file."""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving data: {e}")
        return False

def load_data():
    """Loads data from the JSON file or returns defaults."""
    if not os.path.exists(DATA_FILE):
        return DEFAULT_DATA
    
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            # Merge with defaults to ensure all keys exist (simple way)
            # For a real app, a deep merge is better, but this suffices for top-level keys
            for key in DEFAULT_DATA:
                if key not in data:
                    data[key] = DEFAULT_DATA[key]
            return data
    except Exception as e:
        print(f"Error loading data: {e}")
        return DEFAULT_DATA
