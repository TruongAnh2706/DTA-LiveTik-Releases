"""Integration tests for WebSocket Extension Bridge Server."""

import asyncio
import json

import pytest
import websockets

from dta_autolive.infrastructure.websocket_server import ExtensionBridgeServer


@pytest.mark.asyncio
async def test_websocket_server_handshake_and_command() -> None:
    """Test WebSocket handshake, pairing token validation, and command transmission."""
    test_port = 8769
    server = ExtensionBridgeServer(host="127.0.0.1", port=test_port, pairing_token="test_secret")
    await server.start()

    try:
        async with websockets.connect(f"ws://127.0.0.1:{test_port}") as client:
            # Send HELLO Handshake
            hello_msg = {
                "protocol_version": "1.0",
                "type": "HELLO",
                "extension_version": "1.0.0",
                "pairing_token": "test_secret",
            }
            await client.send(json.dumps(hello_msg))

            raw_resp = await asyncio.wait_for(client.recv(), timeout=2.0)
            resp = json.loads(raw_resp)

            assert resp["type"] == "WELCOME"
            assert server.is_connected is True

            # Send command from server to extension client
            cmd = {
                "protocol_version": "1.0",
                "message_id": "msg_001",
                "type": "PIN_PRODUCT",
                "payload": {"product_id": "999"},
            }
            sent = await server.send_command(cmd)
            assert sent is True

            # Extension receives command
            cmd_received_raw = await asyncio.wait_for(client.recv(), timeout=2.0)
            cmd_received = json.loads(cmd_received_raw)
            assert cmd_received["payload"]["product_id"] == "999"

    finally:
        await server.stop()
