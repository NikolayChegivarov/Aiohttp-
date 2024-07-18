import asyncio

import aiohttp


async def main():
    client = aiohttp.ClientSession()

    response = await client.post(
        'http://127.0.0.1:8080/user',
        json={'name': 'user_2', 'password': '1234'}
    )
    data = await response.text()
    print(data)
    await client.close()

asyncio.run(main())