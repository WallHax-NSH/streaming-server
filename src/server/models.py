from fastapi import WebSocket, WebSocketDisconnect
import logging
import asyncio
import aiofiles
import uuid
from pathlib import Path
from .clients import manager

class Producer:
    session_id: str
    websocket: WebSocket
    
    def __init__(self, session_id: str, websocket: WebSocket):
        self.session_id = session_id
        self.websocket = websocket

    async def _handle_producer_frames(self):
        await self.websocket.accept()

        await manager.connect_producer(self.session_id, self.websocket)
        logging.info(f"[Server] Producer connected ➔ session_id={self.session_id}")
        frames: list[str] = []
        frame_count = 0

        try:
            while True:
                msg = await self.websocket.receive()
                frame_count += 1

                logging.info(f"[Server] Received frame #{frame_count}")
                logging.info(f"[Server] frame type={msg.get('type')} text_present={msg.get('text') is not None} bytes_present={msg.get('bytes') is not None}")

                if msg.get('bytes') is not None:
                    raw_bytes = msg['bytes']
                    logging.info(f"[Server] Echoing collab data ({len(raw_bytes)} bytes)")
                    #await self.websocket.send_bytes(raw_bytes)
                    continue

                guard_text = msg.get('text')
                if guard_text is None:
                    continue
                raw = guard_text

                logging.info(f"[Server] Raw PLY chunk ({raw[:100]}…)")
                frames.append(raw)
                await manager.broadcast(self.session_id, raw)

        except WebSocketDisconnect:
            manager.disconnect_producer(self.session_id, self.websocket)
            logging.info(f"[Server] Producer disconnected after {frame_count} frames ➔ session_id={self.session_id}")
            await self._persist_and_broadcast_file(frames)
        except RuntimeError as e:
            logging.info(f"[Server] receive loop ended after {frame_count} frames: {e}")
            await self._persist_and_broadcast_file(frames)
        
    async def _persist_and_broadcast_file(self, frames: list[str]):
        data = "".join(frames).encode()
        chunk_size = 64 * 1024
        for i in range(0, len(data), chunk_size):
            chunk = data[i : i + chunk_size]
            logging.info(f"[Server] Sending PLY chunk ({len(chunk)} bytes)")
            await manager.broadcast("plyStream", chunk)
        await manager.broadcast("plyStream", "__END__")
        
        logging.info("[Server] Finished broadcasting File to clients")
        asyncio.create_task(self._async_write_file(data))


    async def _handle_refined_data(self):
        await self.websocket.accept()
        await manager.connect_consumer("plyStream", self.websocket)
        logging.info(f"[Server] Producer connected ➔ session_id={self.session_id}")
        frames: list[str] = []
        frame_count = 0

        try:
            while True:
                msg = await self.websocket.receive()
                frame_count += 1

                logging.info(f"[Server] Received frame #{frame_count}")
                logging.info(f"[Server] frame type={msg.get('type')} text_present={msg.get('text') is not None} bytes_present={msg.get('bytes') is not None}")

                if msg.get('bytes') is not None:
                    raw_bytes = msg['bytes']
                    logging.info(f"[Server] Echoing collab data ({len(raw_bytes)} bytes)")
                    await self.websocket.send_bytes(raw_bytes)
                    continue

                guard_text = msg.get('text')
                if guard_text is None:
                    continue
                raw = guard_text

                logging.info(f"[Server] Raw PLY chunk ({raw[:100]}…)")
                frames.append(raw)
                await manager.broadcast("plyStream", raw)

        except WebSocketDisconnect:
            manager.disconnect_producer("plyStream", self.websocket)
            logging.info(f"[Server] Producer disconnected after {frame_count} frames ➔ session_id={self.session_id}")
            await self._persist_and_broadcast_file(frames)
        except RuntimeError as e:
            logging.info(f"[Server] receive loop ended after {frame_count} frames: {e}")
            await self._persist_and_broadcast_file(frames)

        

    async def _async_write_file(self, data: bytes):
        # ensure output directory exists
        output_dir = Path("files")
        output_dir.mkdir(exist_ok=True)
        path = output_dir / f"{uuid.uuid4()}.ply"
        async with aiofiles.open(path, "wb") as f:
            await f.write(data)
        logging.info(f"[Server] Persisted PLY to {path}")


class Consumer:
    session_id: str
    websocket: WebSocket

    def __init__(self, session_id: str, websocket: WebSocket):
        self.session_id = session_id
        self.websocket = websocket

    async def _handle_consumer(self):
        await self.websocket.accept()
        await manager.connect_consumer(self.session_id, self.websocket)
        logging.info(f"[Server] Consumer connected ➔ session_id={self.session_id}")
        try:
            while True:
                await self.websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect_consumer(self.session_id, self.websocket)
            logging.info(f"[Server] Consumer disconnected ➔ session_id={self.session_id}")
