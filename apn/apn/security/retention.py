from __future__ import annotations
import time
from pathlib import Path


def expired_crops(root:Path,retention_hours:float,now:float|None=None)->list[Path]:
    cutoff=(time.time() if now is None else now)-retention_hours*3600
    return [path for path in root.rglob("*.jpg") if path.stat().st_mtime<cutoff]


def purge_expired_crops(root:Path,retention_hours:float,audit:list[dict],now:float|None=None)->int:
    targets=expired_crops(root,retention_hours,now)
    for path in targets:path.unlink()
    audit.append({"action":"privacy.retention_purge","removed":len(targets),"retention_hours":retention_hours})
    return len(targets)
