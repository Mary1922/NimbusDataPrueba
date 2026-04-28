import os
import json
import pytest
from src.storage.json_handler import save_weather_data


def test_save_new_data(tmp_path):
    """Test that new data is successfully saved to a JSON file."""
    test_file = tmp_path / "test_history.json"

    fake_data = {"zone": "Madrid", "date": "2026-04-23", "temperature": 25.5}

    result = save_weather_data(fake_data, file_path=str(test_file))

    assert result is True
    assert os.path.exists(test_file)

    with open(test_file, "r", encoding="utf-8") as f:
        saved_data = json.load(f)
        assert len(saved_data) == 1
        assert saved_data[0]["zone"] == "Madrid"


def test_prevent_duplicates(tmp_path):
    """Test that the system blocks duplicate entries based on zone and date."""
    test_file = tmp_path / "test_history.json"
    fake_data = {"zone": "Madrid", "date": "2026-04-23", "temperature": 25.5}

    save_weather_data(fake_data, file_path=str(test_file))

    result = save_weather_data(fake_data, file_path=str(test_file))

    assert result is False

    with open(test_file, "r", encoding="utf-8") as f:
        saved_data = json.load(f)
        assert len(saved_data) == 1
