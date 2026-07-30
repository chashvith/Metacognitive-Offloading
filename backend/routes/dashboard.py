from fastapi import APIRouter, HTTPException
import os
import json
from pathlib import Path
from typing import List
from services.llm.groq_client import groq_client

router = APIRouter(
    prefix="/api",
    tags=["Dashboard"]
)

# Go up two levels from backend/routes/dashboard.py to get to the project root, then to dataset/
DATASET_DIR = Path(__file__).resolve().parent.parent.parent / "dataset"

@router.get("/sessions")
def list_sessions() -> List[str]:
    """Returns a list of all processed session JSON filenames."""
    if not DATASET_DIR.exists():
        return []
    
    # List all .json files in dataset/ that start with 'session_'
    sessions = []
    for file in DATASET_DIR.iterdir():
        if file.is_file() and file.name.startswith("session_") and file.suffix == ".json":
            sessions.append(file.name)
            
    # Sort by name (which includes timestamp) descending
    sessions.sort(reverse=True)
    return sessions

@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    """Returns the full JSON content of a specific session."""
    if not session_id.endswith(".json"):
        session_id += ".json"
        
    file_path = DATASET_DIR / session_id
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Session not found")
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading session file: {str(e)}")

@router.post("/sessions/{session_id}/summary")
def generate_session_summary(session_id: str):
    """Generates a 3-sentence AI summary of the student's session using Groq."""
    if not session_id.endswith(".json"):
        session_id += ".json"
        
    file_path = DATASET_DIR / session_id
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Session not found")
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        timeline = data.get("timeline", [])
        metrics = data.get("derived_metrics", {})
        
        system_prompt = (
            "You are an expert pedagogical AI analyzing a student's coding session. "
            "Return a strictly formatted JSON object with a single key 'summary'. "
            "The value must be a concise, 3-sentence plain-English summary of the student's learning process, "
            "focusing on where they struggled, what interventions they received, and if they succeeded."
        )
        
        user_prompt = f"Session Metrics: {json.dumps(metrics)}\nTimeline: {json.dumps(timeline)}"
        
        result = groq_client.generate_structured_json(system_prompt, user_prompt)
        
        if result and "summary" in result:
            return {"summary": result["summary"]}
        else:
            return {"summary": "The AI could not generate a summary at this time. Please ensure the API key is configured."}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")
