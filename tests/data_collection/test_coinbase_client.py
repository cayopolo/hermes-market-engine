import asyncio
import json
from collections.abc import Generator
from typing import Never
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import websockets

from src.data_collection.coinbase_client import CoinbaseWebsocketClient


@pytest.fixture
def mock_message_handler() -> AsyncMock:
    """Fixture for a mock message handler."""
    return AsyncMock()


@pytest.fixture
def mock_settings() -> Generator[MagicMock]:
    """Fixture for mock settings."""
    with patch("src.data_collection.coinbase_client.settings") as mock:
        mock.coinbase_ws_url = "wss://test.coinbase.com"
        mock.channel = "ticker"
        mock.product_id = "BTC-USD"
        yield mock


@pytest.fixture
def client(mock_message_handler: AsyncMock) -> CoinbaseWebsocketClient:
    """Fixture for CoinbaseWebsocketClient instance."""
    return CoinbaseWebsocketClient(on_message=mock_message_handler)


class TestCoinbaseWebsocketClient:
    """Test suite for CoinbaseWebsocketClient."""

    @pytest.mark.asyncio
    async def test_successful_connection_and_subscription(
        self, client: CoinbaseWebsocketClient, mock_settings: Generator[MagicMock]
    ) -> None:
        """Test that the client successfully connects and subscribes to the WebSocket."""
        mock_websocket = AsyncMock()
        mock_websocket.recv = AsyncMock(side_effect=websockets.ConnectionClosed(None, None))

        with patch("src.data_collection.coinbase_client.websockets.connect") as mock_connect:
            mock_connect.return_value.__aenter__.return_value = mock_websocket
            mock_connect.return_value.__aexit__.return_value = AsyncMock()

            # Start the client in a task and stop it after a short delay
            task = asyncio.create_task(client.start())
            await asyncio.sleep(0.05)
            await client.stop()

            try:
                await asyncio.wait_for(task, timeout=1.0)
            except TimeoutError:
                task.cancel()

            # Verify connection was established
            mock_connect.assert_called_once_with(mock_settings.coinbase_ws_url, max_size=None, ping_interval=None)  # type: ignore

            # Verify subscription message was sent
            expected_subscription = {"type": "subscribe", "channels": [mock_settings.channel], "product_ids": [mock_settings.product_id]}  # type: ignore
            mock_websocket.send.assert_called_once_with(json.dumps(expected_subscription))

    @pytest.mark.asyncio
    async def test_message_handler_called_with_correct_arguments(
        self, client: CoinbaseWebsocketClient, mock_message_handler: AsyncMock
    ) -> None:
        """Test that the message handler is called with the correct message and timestamp."""
        test_message = json.dumps({"type": "ticker", "price": "50000"})

        mock_websocket = AsyncMock()
        # Return a message, then close the connection
        mock_websocket.recv = AsyncMock(side_effect=[test_message, websockets.ConnectionClosed(None, None)])

        with patch("src.data_collection.coinbase_client.websockets.connect") as mock_connect:
            mock_connect.return_value.__aenter__.return_value = mock_websocket
            mock_connect.return_value.__aexit__.return_value = AsyncMock()

            # Mock the event loop time
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.time.return_value = 123456.789

                # Start the client and let it process one message
                task = asyncio.create_task(client.start())
                await asyncio.sleep(0.05)
                await client.stop()

                try:
                    await asyncio.wait_for(task, timeout=1.0)
                except TimeoutError:
                    task.cancel()

                # Verify the message handler was called with correct arguments
                mock_message_handler.assert_called_once_with(test_message, 123456.789)

    @pytest.mark.asyncio
    async def test_reconnection_on_connection_drop(self, client: CoinbaseWebsocketClient) -> None:
        """Test that the client automatically reconnects after a connection drop."""
        connection_count = 0

        def mock_connect_factory(*args, **kwargs) -> AsyncMock:  # noqa: ANN002, ANN003, ARG001
            nonlocal connection_count
            connection_count += 1

            mock_websocket = AsyncMock()
            mock_websocket.recv = AsyncMock(side_effect=websockets.ConnectionClosed(None, None))

            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_websocket
            mock_ctx.__aexit__.return_value = AsyncMock()

            # Stop after second connection attempt
            if connection_count >= 2:
                client.should_run = False

            return mock_ctx

        with patch("src.data_collection.coinbase_client.websockets.connect") as mock_connect:
            mock_connect.side_effect = mock_connect_factory

            # Mock sleep to speed up the test
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                await client.start()

                # Verify multiple connection attempts were made
                assert connection_count == 2

                # Verify sleep was called between reconnection attempts
                mock_sleep.assert_called_with(3)

    @pytest.mark.asyncio
    async def test_reconnection_with_exception(self, client: CoinbaseWebsocketClient) -> None:
        """Test that the client handles exceptions and reconnects."""
        connection_count = 0

        def mock_connect_factory(*args, **kwargs) -> AsyncMock:  # noqa: ANN002, ANN003, ARG001
            nonlocal connection_count
            connection_count += 1

            if connection_count == 1:
                # First attempt raises an exception immediately
                raise Exception("Connection error")
            else:
                # Second attempt succeeds but then closes
                mock_websocket = AsyncMock()
                mock_websocket.recv = AsyncMock(side_effect=websockets.ConnectionClosed(None, None))

                mock_ctx = AsyncMock()
                mock_ctx.__aenter__.return_value = mock_websocket
                mock_ctx.__aexit__.return_value = AsyncMock()

                client.should_run = False
                return mock_ctx

        with patch("src.data_collection.coinbase_client.websockets.connect") as mock_connect:
            mock_connect.side_effect = mock_connect_factory

            with patch("asyncio.sleep", new_callable=AsyncMock):
                await client.start()

                # Verify reconnection occurred after exception
                assert connection_count == 2

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, client: CoinbaseWebsocketClient) -> None:
        """Test that the client gracefully shuts down when stop is called."""
        mock_websocket = AsyncMock()

        # Make recv block indefinitely until stopped
        async def blocking_recv() -> Never:
            while client.should_run:
                await asyncio.sleep(0.05)
            raise websockets.ConnectionClosed(None, None)

        mock_websocket.recv = blocking_recv

        with patch("src.data_collection.coinbase_client.websockets.connect") as mock_connect:
            mock_connect.return_value.__aenter__.return_value = mock_websocket
            mock_connect.return_value.__aexit__.return_value = AsyncMock()

            # Start the client
            task = asyncio.create_task(client.start())
            await asyncio.sleep(0.05)  # Let it connect

            # Stop the client
            await client.stop()

            # Wait for the task to complete
            try:
                await asyncio.wait_for(task, timeout=2.0)
            except TimeoutError:
                task.cancel()
                pytest.fail("Client did not shut down gracefully")

            # Verify should_run is False
            assert client.should_run is False

            # Verify websocket close was called
            mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_without_active_connection(self, client: CoinbaseWebsocketClient) -> None:
        """Test that stop can be called even without an active connection."""
        # This should not raise any exceptions
        await client.stop()
        assert client.should_run is False

    @pytest.mark.asyncio
    async def test_multiple_messages_processed(self, client: CoinbaseWebsocketClient, mock_message_handler: AsyncMock) -> None:
        """Test that multiple messages are processed correctly."""
        messages = [
            json.dumps({"type": "ticker", "price": "50000"}),
            json.dumps({"type": "ticker", "price": "50100"}),
            json.dumps({"type": "ticker", "price": "50200"}),
        ]

        mock_websocket = AsyncMock()
        mock_websocket.recv = AsyncMock(side_effect=[*messages, websockets.ConnectionClosed(None, None)])

        with patch("src.data_collection.coinbase_client.websockets.connect") as mock_connect:
            mock_connect.return_value.__aenter__.return_value = mock_websocket
            mock_connect.return_value.__aexit__.return_value = AsyncMock()

            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.time.return_value = 123456.789

                task = asyncio.create_task(client.start())
                await asyncio.sleep(0.05)
                await client.stop()

                try:
                    await asyncio.wait_for(task, timeout=1.0)
                except TimeoutError:
                    task.cancel()

                # Verify all messages were processed
                assert mock_message_handler.call_count == len(messages)

    @pytest.mark.asyncio
    async def test_connection_closed_during_recv(self, client: CoinbaseWebsocketClient) -> None:
        """Test handling of connection closure during message reception."""
        mock_websocket = AsyncMock()
        mock_websocket.recv = AsyncMock(side_effect=websockets.ConnectionClosed(None, None))

        with patch("src.data_collection.coinbase_client.websockets.connect") as mock_connect:
            mock_connect.return_value.__aenter__.return_value = mock_websocket
            mock_connect.return_value.__aexit__.return_value = AsyncMock()

            task = asyncio.create_task(client.start())
            await asyncio.sleep(0.05)
            await client.stop()

            # Should complete without raising an exception
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(task, timeout=1.0)
