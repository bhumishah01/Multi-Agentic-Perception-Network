from __future__ import annotations
import json
from pathlib import Path


class PermissionDenied(Exception): pass


class RBAC:
    def __init__(self, roles: dict[str, list[str]]) -> None:
        self.roles = {role:set(permissions) for role,permissions in roles.items()}

    @classmethod
    def load(cls, path: Path) -> "RBAC":
        return cls(json.loads(path.read_text()))

    def allows(self, role: str, permission: str) -> bool:
        return permission in self.roles.get(role,set())

    def require(self, role: str, permission: str) -> None:
        if not self.allows(role,permission):
            raise PermissionDenied(f"{role} lacks {permission}")
