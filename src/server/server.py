import os
import socket
import uvicorn
import logging
from typing import Union

from fastapi import FastAPI, WebSocket, status
from starlette.middleware.cors import CORSMiddleware

from .models import Consumer, Producer

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="LiDAR Data Streaming Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/{role}/{data_stream}")
async def data_streaming_endpoint(
    websocket: WebSocket,
    role:       str,
    data_stream: str
):
    if role == "producer":
        producer = Producer(data_stream, websocket)
        await _handle(producer, data_stream)

    elif role == "consumer":
        consumer = Consumer(data_stream, websocket)
        await _handle(consumer, data_stream)
    
    else:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logging.warning(f"[Server] Rejected unknown role '{role}' LiDAR Stream")


async def _handle(client: Union[Producer, Consumer], data_stream: str):
    if isinstance(client, Producer):
        match data_stream:
            case "plyStream":
                await client._handle_refined_data()
            case _:
                await client._handle_producer_frames()
    elif isinstance(client, Consumer):
        await client._handle_consumer()

def main():
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    port     = int(os.getenv("PORT", "8000"))

    print(f"[Server] Listening on 0.0.0.0:{port}")
    print(f"[Server] → Producer URL: ws://{local_ip}:{port}/ws/producer/{{session_id}}")
    print(f"[Server] → Consumer URL: ws://{local_ip}:{port}/ws/consumer/{{session_id}}\n")

    uvicorn.run(
        "server.server:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info",
        ws_max_size=10*1024*1024
    )

if __name__ == "__main__":
    main()
