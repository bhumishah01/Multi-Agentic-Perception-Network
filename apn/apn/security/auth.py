from __future__ import annotations
import hashlib,hmac,json


class AgentSigner:
    def __init__(self, secrets: dict[str,bytes]) -> None:self.secrets=secrets
    @staticmethod
    def canonical(payload: dict) -> bytes:return json.dumps(payload,sort_keys=True,separators=(",",":")).encode()
    def sign(self,agent_id:str,payload:dict)->str:
        if agent_id not in self.secrets:raise ValueError("unknown agent identity")
        return hmac.new(self.secrets[agent_id],self.canonical(payload),hashlib.sha256).hexdigest()
    def verify(self,agent_id:str,payload:dict,signature:str)->bool:
        if agent_id not in self.secrets:return False
        return hmac.compare_digest(self.sign(agent_id,payload),signature)
