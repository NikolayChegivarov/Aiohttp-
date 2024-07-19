import asyncio

import aiohttp


async def main():
    client = aiohttp.ClientSession()

    # Создаем пользователя.
    # response = await client.post(
    #     'http://127.0.0.1:8080/user',
    #     json={'name': 'user_10', 'password': '1234'}
    # )

    # Просмотр пользователя.
    # response = await client.get(
    #     'http://127.0.0.1:8080/user/3',
    # )

    # Удаление пользователя.
    # response = await client.delete(
    #     'http://127.0.0.1:8080/user/8',
    # )

    # Изменить пользователя.
    # response = await client.patch(
    #     'http://127.0.0.1:8080/user/10',
    #     json={'name': 'new_user2'}
    # )

    # Создаем объявление.
    # response = await client.post(
    #     'http://127.0.0.1:8080/user/4/ads',
    #     json={'title': 'I\'m selling a knife', 'description': 'good knife'}
    # )

    # Просмотр объявления.
    # response = await client.get(
    #     'http://127.0.0.1:8080/ads/7',
    # )

    # Изменить объявление.
    # response = await client.patch(
    #     'http://127.0.0.1:8080/ads/7',
    #     json={'title': 'I\'m selling a knife', 'description': 'bad knife'}
    # )

    # Удаление объявления.
    # response = await client.delete(
    #     'http://127.0.0.1:8080/ads/6',
    # )

    # Просмотр всех объявлений пользователя.
    response = await client.get(
        'http://127.0.0.1:8080/ads/user/4',
    )

    data = await response.text()
    print(data)
    await client.close()

asyncio.run(main())