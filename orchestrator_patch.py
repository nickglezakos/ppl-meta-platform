
# Quick patch for Orchestrator person-objects endpoint
# Add this to your Orchestrator service to return mock PPL Thread results

import json
from pathlib import Path

def get_mock_person_objects(media_id: str):
    """Return mock PPL Thread results for testing"""
    try:
        mock_file = Path("mock_person_objects_data.json")
        if mock_file.exists():
            with open(mock_file, 'r') as f:
                mock_data = json.load(f)
                return mock_data.get(media_id, {
                    "success": False,
                    "media_id": media_id,
                    "total_persons": 0,
                    "total_faces": 0,
                    "status": "no_data",
                    "message": "No person objects data available yet"
                })
    except:
        pass
    
    # Default response
    return {
        "success": False,
        "media_id": media_id,
        "total_persons": 0,
        "total_faces": 0,
        "status": "no_data",
        "message": "No person objects data available yet"
    }

# Use this in your person-objects/{media_id} endpoint:
# return get_mock_person_objects(media_id)
