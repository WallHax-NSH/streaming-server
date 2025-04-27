from typing import Union, List
from fastapi import WebSocket
import logging

class ConnectionManager:
    def __init__(self):
        # allow multiple producers per session
        self.producers: dict[str, List[WebSocket]] = {}
        self.consumers: dict[str, list[WebSocket]] = {}

    async def connect_producer(self, session_id: str, ws: WebSocket):
        # append new producer socket
        self.producers.setdefault(session_id, []).append(ws)

    async def connect_consumer(self, session_id: str, ws: WebSocket):
        self.consumers.setdefault(session_id, []).append(ws)

    def disconnect_producer(self, session_id: str, ws: WebSocket):
        # remove this producer; keep consumers alive
        prods = self.producers.get(session_id, [])
        if ws in prods:
            prods.remove(ws)
        if not prods:
            self.producers.pop(session_id, None)

    def disconnect_consumer(self, session_id: str, ws: WebSocket):
        self.consumers.get(session_id, []).remove(ws)

    async def broadcast(self, session_id: str, message: Union[str, bytes]):
        """Send raw text PLY data to all consumers."""
        for consumer in self.consumers.get(session_id, []):
            try:
                if isinstance(message, str):
                    logging.info(f"[Server] Forwarding to consumer: {message[:100]}…")  # optional extra log :contentReference[oaicite:7]{index=7}
                    await consumer.send_text(message)                                           # send as text :contentReference[oaicite:8]{index=8}
                else:
                    logging.info(f"[Server] Forwarding to consumer: {message[:100]}…")
                    await consumer.send_bytes(message)                                          # send as bytes :contentReference[oaicite:9]{index=9}
            except Exception as e:
                logging.error(f"[Server] Broadcast error: {e}")                            # catch send errors :contentReference[oaicite:10]{index=10}



# singleton
manager = ConnectionManager()
