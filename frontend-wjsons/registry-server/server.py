# registry-server/server.py
from __future__ import annotations
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from pathlib import Path
import json

app = FastAPI(title="Mapping Registry", version="1.0.0")

# Allow your Next.js site to call this in dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models -------------------------------------------------
class Mapping(BaseModel):
    id: str
    boardId: str
    partId: str
    role: str
    pins: List[int] = Field(default_factory=list)
    label: Optional[str] = None

class MappingBatch(BaseModel):
    mappings: List[Mapping] = Field(default_factory=list)

# --- Storage ------------------------------------------------
DATA_FILE = Path(__file__).with_name("mappings.json")

def load_all() -> List[dict]:
    if not DATA_FILE.exists():
        return []
    try:
        return json.loads(DATA_FILE.read_text())
    except Exception:
        return []

def save_all(items: List[dict]) -> None:
    DATA_FILE.write_text(json.dumps(items, indent=2))

# --- Routes -------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True}

@app.get("/mappings")
def get_mappings():
    return {"mappings": load_all()}

@app.post("/mappings", status_code=201)
def add_mappings(batch: MappingBatch):
    if not batch.mappings:
        raise HTTPException(400, "No mappings provided")
    current = load_all()
    # naive merge by id (replace if same id)
    ids = {m["id"] for m in current}
    for m in batch.mappings:
        d = m.model_dump()
        if m.id in ids:
            current = [d if x["id"] == m.id else x for x in current]
        else:
            current.append(d)
    save_all(current)
    return {"ok": True, "count": len(batch.mappings)}

@app.delete("/mappings/{mapping_id}")
def delete_mapping(mapping_id: str):
    current = load_all()
    new = [m for m in current if m.get("id") != mapping_id]
    if len(new) == len(current):
        raise HTTPException(404, "Mapping not found")
    save_all(new)
    return {"ok": True}
