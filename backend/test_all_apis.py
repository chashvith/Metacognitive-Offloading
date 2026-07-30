"""Comprehensive API Test Suite for FastAPI Backend."""

import sys
from pathlib import Path

# Ensure backend directory is on sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_health_endpoint():
    """Test GET /health"""
    print("\n[1/5] Testing GET /health...")
    response = client.get("/health")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data.get("status") == "running", f"Unexpected response data: {data}"
    print("  [OK] GET /health PASSED:", data)


def test_predict_solver_endpoint():
    """Test POST /predict/solver"""
    print("\n[2/5] Testing POST /predict/solver...")
    valid_payload = {
        "snapshot": {
            "difficulty": "Easy",
            "language": "python",
            "topic": "Arrays",
            "subtopic": "Two Pointers",
            "elapsed_time": 92.0,
            "progress_ratio": 0.56,
            "current_struggle_score": 0.125,
            "chars_typed": 251,
            "chars_deleted": 19,
            "pause_count": 1,
            "pause_duration": 6.7,
            "compile_attempts": 1,
            "compile_errors": 1,
            "successful_runs": 0,
            "runtime_errors": 0,
            "deletion_ratio": 0.075,
            "typing_speed": 163.7,
            "compile_failure_rate": 1.0,
            "average_pause_duration": 6.7
        }
    }
    response = client.post("/predict/solver", json=valid_payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert "prediction" in data and "confidence" in data, f"Invalid keys in response: {data}"
    print("  [OK] POST /predict/solver PASSED:", data)

    # Invalid payload test
    invalid_payload = {"snapshot": {"elapsed_time": -50}}
    inv_response = client.post("/predict/solver", json=invalid_payload)
    assert inv_response.status_code == 400, f"Expected 400 for invalid snapshot, got {inv_response.status_code}"
    print("  [OK] POST /predict/solver invalid payload handling PASSED (400 Bad Request)")


def test_predict_hint_endpoint():
    """Test POST /predict/hint"""
    print("\n[3/5] Testing POST /predict/hint...")
    payload = {
        "snapshot": {
            "elapsed_time": 132.0,
            "progress_ratio": 0.80,
            "current_struggle_score": 0.183,
            "chars_typed": 252,
            "chars_deleted": 19,
            "pause_count": 3,
            "pause_duration": 49.79,
            "compile_attempts": 3,
            "compile_errors": 2,
            "successful_runs": 1,
            "runtime_errors": 0,
            "deletion_ratio": 0.0754,
            "typing_speed": 114.55,
            "compile_failure_rate": 0.6667,
            "average_pause_duration": 16.60
        }
    }
    response = client.post("/predict/hint", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert "prediction" in data and "confidence" in data, f"Invalid keys in response: {data}"
    print("  [OK] POST /predict/hint PASSED:", data)


def test_predict_full_endpoint():
    """Test POST /predict/full"""
    print("\n[4/5] Testing POST /predict/full...")
    payload = {
        "snapshot": {
            "difficulty": "Medium",
            "language": "java",
            "elapsed_time": 200.0,
            "progress_ratio": 0.40,
            "current_struggle_score": 0.45
        }
    }
    response = client.post("/predict/full", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert "solver" in data and "hint" in data, f"Missing solver/hint in response: {data}"
    print("  [OK] POST /predict/full PASSED:")
    print("    - Solver output:", data["solver"])
    print("    - Hint output:", data["hint"])


def test_recommend_endpoint():
    """Test POST /recommend"""
    print("\n[5/5] Testing POST /recommend...")
    high_struggle_payload = {
        "problem_name": "Two Sum",
        "topic": "Arrays",
        "subtopic": "HashMaps",
        "language": "Java",
        "solver_prediction": "Needs Help",
        "hint_prediction": "Concept Hint",
        "snapshot": {
            "current_struggle_score": 0.75,
            "compile_errors": 6,
            "pause_duration": 120.0
        }
    }
    response = client.post("/recommend", json=high_struggle_payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data.get("level") == "concept", f"Expected 'concept' level, got {data}"
    assert "title" in data and "message" in data and "reflection_question" in data
    assert "next_step" in data and "encouragement" in data and "confidence" in data
    print("  [OK] POST /recommend PASSED:", data)



def run_all_tests():
    print("=" * 60)
    print("STARTING FULL API TEST SUITE")
    print("=" * 60)
    test_health_endpoint()
    test_predict_solver_endpoint()
    test_predict_hint_endpoint()
    test_predict_full_endpoint()
    test_recommend_endpoint()
    print("=" * 60)
    print("ALL API ENDPOINTS TESTED SUCCESSFULLY! READY TO PUSH CODE.")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
