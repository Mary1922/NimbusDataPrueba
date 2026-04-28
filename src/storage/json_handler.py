import json
import os

def save_weather_data(new_data, file_path="data/history.json"):
    """
    Saves clean weather data to a JSON file without overwriting history.
    Prevents duplicate entries based on 'date' and 'zone'.
    """
    historical_data = []

    # Ensure the data directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Step 1: Read the existing historical data
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            try:
                historical_data = json.load(file)
            except json.JSONDecodeError:
                historical_data = []

    # Step 2: Check for duplicates
    for entry in historical_data:
        if entry.get("zone") == new_data.get("zone") and entry.get("date") == new_data.get("date"):
            print(f"⚠️ Duplicate detected for {new_data.get('zone')} on {new_data.get('date')}. Skipping.")
            return False

    # Step 3: Append and save
    historical_data.append(new_data)
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(historical_data, file, indent=4, ensure_ascii=False)
    
    print(f"✅ Data safely saved for {new_data.get('zone')}.")
    return True