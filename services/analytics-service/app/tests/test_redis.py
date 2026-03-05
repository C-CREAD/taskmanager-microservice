# test_redis.py
import asyncio
import redis.asyncio as redis


async def test_redis():
    try:
        # Try to connect
        client = await redis.from_url(
            "redis://localhost:6379/3",
            decode_responses=True
        )

        # Test ping
        pong = await client.ping()
        print(f"Ping test: {pong}")

        # Test set/get
        await client.set("test_key", "Hello Redis!")
        value = await client.get("test_key")
        print(f"Get test: {value}")

        # Clean up
        await client.delete("test_key")
        await client.close()

        print("✅ All Redis tests passed!")
        return True

    except Exception as e:
        print(f"❌ Redis test failed: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(test_redis())