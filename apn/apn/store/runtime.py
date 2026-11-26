from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class RuntimeStore:
    def __init__(self, path: Path) -> None:
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("""CREATE TABLE IF NOT EXISTS decisions(
          id INTEGER PRIMARY KEY AUTOINCREMENT, target TEXT NOT NULL, target_id TEXT,
          decision TEXT NOT NULL, note TEXT NOT NULL, role TEXT NOT NULL,
          created_at TEXT NOT NULL)""")
        self.connection.commit()

    def add(self, target: str, target_id: str | None, decision: str, note: str, role: str) -> dict:
        created = datetime.now(timezone.utc).isoformat()
        cursor = self.connection.execute(
            "INSERT INTO decisions(target,target_id,decision,note,role,created_at) VALUES(?,?,?,?,?,?)",
            (target, target_id, decision, note, role, created))
        self.connection.commit()
        return {"record_id": cursor.lastrowid, "target": target, "id": target_id,
                "decision": {"decision": decision, "note": note}, "role": role, "created_at": created}

    def all(self) -> list[dict]:
        return [{"record_id": row["id"], "target": row["target"], "id": row["target_id"],
                 "decision": {"decision": row["decision"], "note": row["note"]},
                 "role": row["role"], "created_at": row["created_at"]}
                for row in self.connection.execute("SELECT * FROM decisions ORDER BY id")]

    def overrides(self) -> dict[str, str]:
        rows = self.connection.execute(
            "SELECT target_id,decision FROM decisions WHERE target='handoff' ORDER BY id").fetchall()
        return {row["target_id"]: row["decision"] for row in rows}


def recompute_entities(data: dict, overrides: dict[str, str]) -> dict:
    """Rebuild connected identity components after human accept/reject decisions."""
    handoffs = [dict(item) for item in data.get("handoffs", [])]
    tracks: set[str] = set()
    edges: list[tuple[str, str]] = []
    for item in handoffs:
        decision = overrides.get(item["handoff_id"])
        if decision in {"accept", "accepted", "approve"}:
            item["state"], item["human_override"] = "accepted", decision
        elif decision in {"reject", "rejected"}:
            item["state"], item["human_override"] = "rejected", decision
        left = f'{item["source_camera"]}:{item["source_track"]}'
        right = f'{item["target_camera"]}:{item["target_track"]}'
        tracks.update((left, right))
        if item["state"] == "accepted":
            edges.append((left, right))
    parent = {track: track for track in tracks}
    def find(value: str) -> str:
        while parent[value] != value:
            parent[value] = parent[parent[value]]; value = parent[value]
        return value
    for left, right in edges:
        a, b = find(left), find(right)
        if a != b: parent[b] = a
    by_track = {f'{step["camera_id"]}:{step["local_track_id"]}': step
                for entity in data.get("entities", []) for step in entity.get("journey", [])}
    components: dict[str, list[str]] = {}
    for track in sorted(tracks): components.setdefault(find(track), []).append(track)
    entities = []
    for index, members in enumerate(sorted(components.values(), key=lambda x: (-len(x), x)), 1):
        journey = sorted((by_track[x] for x in members if x in by_track), key=lambda x: x["start"])
        entities.append({"entity_id": f"E-{index:03d}", "label": f"Entity {index:03d}",
                         "status": "active", "member_tracks": members, "journey": journey,
                         "confidence_state": "accepted" if len(members) > 1 else "unlinked"})
    return {**data, "handoffs": handoffs, "entities": entities}
