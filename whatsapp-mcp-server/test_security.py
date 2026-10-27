import asyncio
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import main
import whatsapp


class SecurityTests(unittest.TestCase):
    def test_upstream_results_survive_mcp_serialization(self):
        # New MCP SDKs otherwise validate the old, inaccurate Dict annotations.
        with patch.object(main, "whatsapp_list_chats", return_value=[whatsapp.Chat(jid="fixture@g.us", name="Fixture", last_message_time=None)]), patch.object(main, "whatsapp_list_messages", return_value="fixture text"):
            asyncio.run(main.mcp.call_tool("list_chats", {"limit": 1}))
            asyncio.run(main.mcp.call_tool("list_messages", {"limit": 1}))

    def test_read_only_tool_discovery(self):
        tools = asyncio.run(main.mcp.list_tools())
        names = {tool.name for tool in tools}
        self.assertEqual(len(names), 9)
        self.assertTrue({"list_chats", "download_media"} <= names)
        self.assertFalse({"send_message", "send_file", "send_audio_message"} & names)

    def test_send_functions_deny_before_io(self):
        with patch.dict(os.environ, {"WHATSAPP_ENABLE_SEND": "0"}), patch("whatsapp.api_post") as post:
            self.assertFalse(whatsapp.send_message("test", "test")[0])
            self.assertFalse(whatsapp.send_file("test", "/nonexistent")[0])
            self.assertFalse(whatsapp.send_audio_message("test", "/nonexistent")[0])
            post.assert_not_called()

    def test_remote_api_denied(self):
        with patch.object(whatsapp, "WHATSAPP_API_BASE_URL", "http://example.com:8080/api"):
            with self.assertRaises(ValueError):
                whatsapp.api_post({}, "download")

    def test_authenticated_request_disables_proxy_and_redirects(self):
        with tempfile.TemporaryDirectory() as directory:
            token = Path(directory) / "api-token"
            token.write_text("x" * 64)
            token.chmod(0o600)
            with patch.dict(os.environ, {"WHATSAPP_API_TOKEN_FILE": str(token)}), patch("whatsapp.requests.Session") as factory:
                session = factory.return_value.__enter__.return_value
                whatsapp.api_post({"message_id": "fixture"}, "download")
                self.assertFalse(session.trust_env)
                kwargs = session.post.call_args.kwargs
                self.assertEqual(kwargs["headers"]["Authorization"], "Bearer " + "x" * 64)
                self.assertFalse(kwargs["allow_redirects"])
                self.assertEqual(kwargs["timeout"], (5, 120))


if __name__ == "__main__":
    unittest.main()
