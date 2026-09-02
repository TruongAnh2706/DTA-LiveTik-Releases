"""Async WebSocket Server for Chrome Extension Bridge communication."""

import json
from collections.abc import Callable
from typing import Any

import structlog
import websockets
from websockets.server import WebSocketServerProtocol  # type: ignore[attr-defined]

logger = structlog.get_logger()


class ExtensionBridgeServer:
    """Async WebSocket Server running on localhost for Chrome Extension integration."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        pairing_token: str = "dta_secret_token_123",
    ) -> None:
        self.host = host
        self.port = port
        self.pairing_token = pairing_token
        self._server: Any = None
        self._connected_clients: set[WebSocketServerProtocol] = set()
        self._is_paired: bool = False
        self._command_callbacks: list[Callable[[dict[str, Any]], None]] = []

    @property
    def is_connected(self) -> bool:
        """Check if at least one client is connected."""
        return len(self._connected_clients) > 0

    async def start(self) -> None:
        """Start the WebSocket server on localhost."""
        self._server = await websockets.serve(self._handle_client, self.host, self.port)
        logger.info("extension_bridge_started", host=self.host, port=self.port)

    async def stop(self) -> None:
        """Stop the WebSocket server and close client connections."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("extension_bridge_stopped")

    def register_command_callback(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Register callback for received ACK/responses from Extension."""
        self._command_callbacks.append(callback)

    async def send_command(self, command_data: dict[str, Any]) -> bool:
        """Send command message to all connected clients (Electron UI & Extension)."""
        if not self._connected_clients:
            logger.warning("send_command_failed_no_connected_clients")
            return False

        message = json.dumps(command_data)
        success = True
        for ws in list(self._connected_clients):
            try:
                await ws.send(message)
                logger.info("command_sent_to_client", message_type=command_data.get("type"))
            except Exception as e:
                logger.error("error_sending_command", error=str(e))
                success = False
        return success

    async def _handle_client(self, websocket: Any) -> None:
        """Handle incoming WebSocket connection lifecycle."""
        logger.info(
            "extension_client_connecting", remote=getattr(websocket, "remote_address", "unknown")
        )
        self._connected_clients.add(websocket)
        try:
            async for raw_msg in websocket:
                try:
                    data = json.loads(raw_msg)
                    await self._process_message(websocket, data)
                except json.JSONDecodeError:
                    logger.error("invalid_json_received")
        except Exception:
            logger.info("extension_client_disconnected")
        finally:
            self._connected_clients.discard(websocket)
            if len(self._connected_clients) == 0:
                self._is_paired = False

    async def _process_message(
        self, websocket: WebSocketServerProtocol, data: dict[str, Any]
    ) -> None:
        """Process incoming JSON messages from Extension or Electron UI."""
        msg_type = data.get("type")

        if msg_type == "HELLO":
            token = data.get("pairing_token")
            if token == self.pairing_token:
                self._is_paired = True
                response = {
                    "protocol_version": "1.0",
                    "type": "WELCOME",
                    "connection_id": "conn_" + str(id(websocket)),
                    "heartbeat_interval_ms": 5000,
                }
                await websocket.send(json.dumps(response))
                logger.info("extension_paired_successfully")
            else:
                err_resp = {
                    "type": "ERROR",
                    "code": "NOT_PAIRED",
                    "message": "Invalid pairing token",
                }
                await websocket.send(json.dumps(err_resp))

        # Forward all command messages to registered backend service callbacks
        for cb in list(self._command_callbacks):
            try:
                cb(data)
            except Exception as e:
                logger.error("error_in_command_callback", error=str(e))
