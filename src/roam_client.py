from typing import Any, Dict, List, Optional

import requests


class RoamClient:
    BASE = "https://api.ro.am/v1"

    def __init__(self, api_token: str = "") -> None:
        self.api_token = api_token.strip()
        self.session = requests.Session()
        if self.api_token:
            self.session.headers.update({"Authorization": f"Bearer {self.api_token}"})
        self.session.headers.update({"Content-Type": "application/json", "Accept": "application/json"})

    def post_message(self, chat_id: str, text: str) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "recipients": [chat_id],
            "text": text,
            "sender": {
                "id": "jira-agent",
                "name": "Jira Agent",
                "imageUrl": "https://cdn.worldvectorlogo.com/logos/jira-1.svg",
            },
        }
        resp = self.session.post(f"{self.BASE}/chat.sendMessage", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def list_chats(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Lista todos los chats accesibles (channels, DMs, groups)."""
        chats: List[Dict[str, Any]] = []
        cursor: Optional[str] = None
        while True:
            params: Dict[str, Any] = {"limit": min(limit, 100)}
            if cursor:
                params["cursor"] = cursor
            resp = self.session.get(f"{self.BASE}/chat.list", params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            page = data.get("chats") or data.get("items") or []
            chats.extend(page)
            cursor = data.get("nextCursor") or data.get("cursor")
            if not cursor or len(page) == 0:
                break
        return chats

    def find_channel_id(self, name: str) -> Optional[str]:
        """Busca un canal por nombre y devuelve su ID."""
        chats = self.list_chats()
        name_lower = name.lower()
        for chat in chats:
            chat_name = (chat.get("name") or "").lower()
            if chat_name == name_lower:
                return chat.get("id") or chat.get("chatId")
        return None

    # Compatibilidad con el contrato viejo usado en main.py
    def post_update(self, webhook_url: str, title: str, body: str) -> None:
        """Fallback: POST genérico a un webhook URL arbitrario."""
        payload: Dict[str, Any] = {"title": title, "body": body}
        resp = self.session.post(webhook_url, json=payload, timeout=30)
        resp.raise_for_status()
