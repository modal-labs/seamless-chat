import pytest, asyncio, aiohttp, pytest_asyncio, os
from typing import Dict, Any

BASE_URL = os.getenv("PUBLIC_BACKEND_URL")

@pytest_asyncio.fixture
async def session():
    async with aiohttp.ClientSession() as session:
        yield session

@pytest.mark.asyncio
async def test_create_room(session):
    async with session.post(f"{BASE_URL}/create-room") as response:
        assert response.status == 200
        data = await response.json()
        assert "roomId" in data
        assert isinstance(data["roomId"], str)

@pytest.mark.asyncio
async def test_join_room(session):
    # First, create a room
    async with session.post(f"{BASE_URL}/create-room") as response:
        room_data = await response.json()
        room_id = room_data["roomId"]

    # Now, join the room
    join_data = {
        "user_name": "TestUser",
        "lang": "eng",
        "room_id": room_id
    }
    async with session.post(f"{BASE_URL}/join-room", data=join_data) as response:
        assert response.status == 200
        data = await response.json()
        assert "userId" in data
        assert isinstance(data["userId"], str)

@pytest.mark.asyncio
async def test_get_rooms(session):
    async with session.get(f"{BASE_URL}/rooms") as response:
        assert response.status == 200
        data = await response.json()
        assert isinstance(data, dict)
        for room_id, room_info in data.items():
            assert isinstance(room_id, str)
            assert "name" in room_info
            assert "members" in room_info

@pytest.mark.asyncio
async def test_get_room_info(session):
    # First, create a room
    async with session.post(f"{BASE_URL}/create-room") as response:
        room_data = await response.json()
        room_id = room_data["roomId"]

    # Now, get room info
    async with session.get(f"{BASE_URL}/room-info?room_id={room_id}") as response:
        assert response.status == 200
        data = await response.json()
        assert "name" in data
        assert "members" in data
        assert isinstance(data["members"], dict)

@pytest.mark.asyncio
async def test_websocket_chat():
    async def connect_and_chat(user_name: str, lang: str) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            # Create and join a room
            async with session.post(f"{BASE_URL}/create-room") as response:
                room_data = await response.json()
                room_id = room_data["roomId"]

            join_data = {
                "user_name": user_name,
                "lang": lang,
                "room_id": room_id
            }
            async with session.post(f"{BASE_URL}/join-room", data=join_data) as response:
                user_data = await response.json()
                user_id = user_data["userId"]

            # Connect to WebSocket
            async with session.ws_connect(f"{BASE_URL}/chat") as ws:
                await ws.send_json({"user_id": user_id, "room_id": room_id, "lang": lang})

                # Send a message
                await ws.send_json({
                    "message_type": "text",
                    "content": "Hello, World!"
                })

                # Wait for a response
                response = await ws.receive_json(timeout=10)
                await ws.close()

                return response

    # Test with two users
    results = await asyncio.gather(
        connect_and_chat("User1", "eng"),
        connect_and_chat("User2", "fra")
    )

    for result in results:
        assert "messageId" in result
        assert "userId" in result
        assert "userName" in result
        assert "lang" in result
        assert "text" in result
        assert "audio" in result
        assert isinstance(result["audio"], list)
    

if __name__ == "__main__":
    pytest.main([__file__])
