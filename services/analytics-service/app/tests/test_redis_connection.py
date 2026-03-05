import socket
import redis
import asyncio
import redis.asyncio as redis_async


def test_redis_sync():
    """Test synchronous Redis connection"""
    try:
        # Test basic socket connection first
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex(('localhost', 6379))
        if result == 0:
            print("✅ Port 6379 is open")
        else:
            print(f"❌ Port 6379 is closed or not listening (error code: {result})")
        sock.close()

        # Test Redis client
        client = redis.Redis(
            host='localhost',
            port=6379,
            db=3,
            socket_connect_timeout=3,
            socket_timeout=3
        )
        client.ping()
        print("✅ Redis sync connection successful")
        client.close()
        return True
    except redis.ConnectionError as e:
        print(f"❌ Redis connection failed: {e}")
        return False
    except socket.gaierror as e:
        print(f"❌ Socket gaierror: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


async def test_redis_async():
    """Test async Redis connection"""
    try:
        client = redis_async.Redis(
            host='localhost',
            port=6379,
            db=3,
            socket_connect_timeout=3,
            socket_timeout=3,
            decode_responses=True
        )
        await client.ping()
        print("✅ Redis async connection successful")
        await client.close()
        return True
    except redis_async.ConnectionError as e:
        print(f"❌ Redis async connection failed: {e}")
        return False
    except socket.gaierror as e:
        print(f"❌ Socket gaierror in async: {e}")
        return False


async def main():
    print("Testing Redis connections...")
    print("-" * 40)

    # Test sync
    sync_result = test_redis_sync()

    # Test async
    async_result = await test_redis_async()

    print("-" * 40)
    if sync_result and async_result:
        print("✅ All Redis tests passed!")
    else:
        print("❌ Some tests failed. Check Redis installation.")


if __name__ == "__main__":
    asyncio.run(main())