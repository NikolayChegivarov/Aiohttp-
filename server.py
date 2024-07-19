from aiohttp import web  # Aсинхронная клиент-серверная HTTP-библиотека для asyncio и Python
import json
from models import Base, engine, Session, User, Ads
from sqlalchemy.exc import InvalidRequestError
import bcrypt  # Для безопасного хеширования паролей.
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from typing import List

app = web.Application()   # Создаем экземпляр класса web


def hash_password(password: str) -> str:
    """Функция для хеширования паролей."""
    password = password.encode()  # Преобразуется в байтовую последовательность. Это необходимо для работы с bcrypt
    password = bcrypt.hashpw(password, bcrypt.gensalt())  # Возвращает хеш-пароля в виде байтовой последовательности.
    password = password.decode()  # Декодирование хеша в строковый формат для удобства использования результата.
    return password


def check_password(pasword: str, hashed_password: str) -> bool:
    """Для авторизации. Возвращает булевое значение True или False"""
    password = pasword.encode()
    hashed_password = hashed_password.encode()
    return bcrypt.checkpw(password, hashed_password)


async def orm_context(app):  # Определение асинхронной функции, которая принимает объект приложения как аргумент.
    print("start")  # Выводит сообщение о начале работы контекста.

    async with engine.begin() as conn:  # Асинхронный блок `with`, который управляет транзакцией базы данных.
        await conn.run_sync(
            Base.metadata.create_all)  # Выполняет синхронную операцию создания всех таблиц, определенных в метаданных.

    yield  # Передача управления обратно вызывающему коду, позволяя ему использовать контекст.

    await engine.dispose()  # Асинхронное освобождение ресурсов движка после завершения работы с базой данных.
    print("SHUTDOWN")  # Выводит сообщение о завершении работы контекста.


# Позволяет определить session_middleware как промежуточное ПО для обработки запросов в приложении.
# Промежуточное ПО выполняется перед тем, как запрос достигнет конечного обработчика.
@web.middleware
# Принимает два аргумента: объект запроса (request) и обработчик запроса (handler).
# Эта функция будет использоваться для управления сессиями пользователей.
async def session_middleware(request: web.Request, handler):
    """Функция session_middleware является асинхронным промежуточным слоем.
    Предназначена для управления сессиями пользователей в рамках обработки HTTP-запросов."""
    async with Session() as session:  # Контекстный менеджер для автоматического закрытия сессии после завершения блока.
        request.session = session  # Назначение созданной сессии объекту запроса.
        response = await handler(request)  # Вызов обработчика запроса с передачей ему объекта запроса.
        return response

# Гарантирует, что контекст базы данных будет корректно очищен после завершения работы приложения.
app.cleanup_ctx.append(orm_context)
# Добавление определенного ранее промежуточного слоя (session_middleware) в список промежуточных слоев приложения.
# Это указывает, что этот слой должен быть применен ко всем запросам, проходящим через приложение.
app.middlewares.append(session_middleware)


async def get_http_error(error_class, msg):
    """Обработчик ошибок."""
    return error_class(
        text=json.dumps({"error": msg}),
        content_type='aplication/json'
    )


async def get_user(session: Session, user_id: int) -> User:
    """Получение id пользователя из сессии."""
    user = await session.get(User, user_id)
    if user is None:
        raise get_http_error(web.HTTPFound, 'User not found')
    return user


async def get_ads(session: Session, ads_id: int) -> Ads:
    """Получаем объявление."""
    ads = await session.get(Ads, ads_id)
    if ads is None:
        raise get_http_error(web.HTTPFound, 'Ads not found')
    return ads


async def add_user(session: Session, user: User):
    """Асинхронная функция для добавления пользователя в базу данных."""
    try:
        # Добавление объекта пользователя в сессию
        session.add(user)
        # Асинхронное выполнение операции коммита в базе данных.
        await session.commit()
        # Возврат добавленного пользователя после успешного сохранения.
        return user
    # Обработка исключения InvalidRequestError, которое может возникнуть при некорректном запросе
    except InvalidRequestError:
        # Вызов функции для генерации HTTP ошибки конфликта, если пользователь уже существует
        raise get_http_error(web.HTTPConflict, 'user already exists')
    # Если до этого момента код не был прерван исключением, функция завершается здесь
    return user


async def add_ads(session: Session, ads: Ads):
    """Асинхронная функция для добавления пользователя в базу данных."""
    try:
        # Добавление объекта объявления в сессию.
        session.add(ads)
        # Асинхронное выполнение операции коммита в базе данных.
        await session.commit()
        # Возврат добавленного объявления после успешного сохранения.
        return ads
    # Обработка исключения InvalidRequestError, которое может возникнуть при некорректном запросе.
    except InvalidRequestError:
        # Вызов функции для генерации HTTP ошибки конфликта, если объявление уже существует.
        raise get_http_error(web.HTTPConflict, 'user already exists')
    # Если до этого момента код не был прерван исключением, функция завершается здесь.
    return ads


async def get_all_ads_for_user(session: Session, user_id: int):
    """Для получения всех объявлений."""
    stmt = select(Ads).where(Ads.owner_id == user_id)
    result = await session.execute(stmt)
    ads_list = result.scalars().all()
    return ads_list


class UserView(web.View):

    @property  # Декоратор @property позволяет обращаться к методу как к атрибуту
    def session(self) -> Session:
        return self.request.session  # Возвращает текущую сессию запроса

    @property
    def user_id(self) -> int:  # Аналогично предыдущему, возвращает идентификатор пользователя из URL.
        return int(self.request.match_info["user_id"])  # Извлекает "user_id" из информации о маршруте запроса.

    async def get(self):  # Асинхронный обработчик GET-запросов
        """Для просмотра пользователя."""
        user = await get_user(self.session, self.user_id)  # Получает информацию о пользователе асинхронно.
        return web.json_response({  # Возвращает JSON-ответ с информацией о пользователе
            'id': user.id,  # Идентификатор пользователя
            'name': user.name,  # Имя пользователя
            'registration_time': int(user.registration_time.timestamp())  # Время регистрации пользователя.
        })

    async def post(self):  # Определение асинхронного метода post
        """Для создания пользователя."""
        json_data = await self.request.json()  # Асинхронное получение JSON из запроса
        print(json_data)
        json_data["password"] = hash_password(
            json_data["password"])  # Хеширование пароля перед сохранением пользователя
        user = User(**json_data)  # Создание объекта User с данными из JSON
        user = await add_user(self.session, user)  # Асинхронная добавление пользователя в базу данных
        response_message = {
            "id": user.id,
            "name": user.name,
            "status": "created"
        }
        return web.json_response(response_message)

    async def patch(self):
        """Для исправления данных пользователя."""
        try:
            user = await get_user(self.session, self.user_id)  # Получаем пользователя.
            old_name = user.name  # Сохраняем старое имя пользователя
            json_data = await self.request.json()  # Извлекаем JSON данные из запроса.
            if "password" in json_data:  # Если в исправляемых данных присутствует пароль, то...
                json_data["password"] = hash_password(json_data["password"])  # ...хешируем пароль перед сохранением.
            for field, value in json_data.items():  # Применяем изменения к объекту пользователя
                setattr(user, field, value)
            await add_user(self.session, user)  # Сохраняем обновленного пользователя в базе данных
            response_message = {
                "id": user.id,
                "It was": old_name,  # Отображаем старое имя
                "It became": user.name,  # Отображаем новое имя
                "status": "has been changed"  # Статус изменено.
            }
            return web.json_response(response_message)
        except IntegrityError as e:
            if 'UniqueViolationError' in str(e.orig):  # Проверяем, связана ли ошибка с нарушением уникальности.
                return web.json_response({"error": "A user with this name already exists."}, status=400)
            else:
                raise  # Перебрасываем другую ошибку, если она возникла

    async def delete(self):
        """Для удаления пользователя."""
        user = await get_user(self.session, self.user_id)  # Получаем пользователя.
        await self.session.delete(user)
        await self.session.commit()
        response_message = {
            "id": user.id,
            "name": user.name,
            "status": "delete"
        }
        return web.json_response(response_message)


class AdsView(web.View):

    @property  # Декоратор @property позволяет обращаться к методу как к атрибуту
    def session(self) -> Session:
        print(self.request.session)
        return self.request.session  # Возвращает текущую сессию запроса

    @property
    def user_id(self) -> int:  # Аналогично предыдущему, возвращает идентификатор пользователя из URL.
        print(f'match_info = {self.request.match_info}')
        try:
            return int(self.request.match_info["user_id"])  # Извлекает "user_id" из информации о маршруте запроса.
        except KeyError:
            return None

    @property
    def ads_id(self) -> int:  # Аналогично предыдущему, возвращает идентификатор пользователя из URL.
        return int(self.request.match_info["ads_id"])  # Извлекает "user_id" из информации о маршруте запроса.

    async def get(self):
        """Для просмотра объявления."""

        ads = await get_ads(self.session, self.ads_id)  # Получает информацию об объявлении асинхронно.
        print(dir(ads))
        return web.json_response({  # Возвращает JSON-ответ с информацией об объявлении.
            'ads_id': ads.ads_id,  # Идентификатор объявления.
            'title': ads.title,  # Заголовок объявления.
            'description': ads.description,  # Описание объявления.
            "owner_id": ads.owner_id  # Автор
        })

    async def post(self):
        """Дописать если объявление уже сущесвует, если пользователь не найден."""
        json_data = await self.request.json()

        print(f'post json_data = {json_data}')

        owner = await get_user(self.session, self.user_id)

        if not owner:
            return web.json_response({"error": "Owner not found"}, status=404)

        ads = Ads(**json_data, owner=owner)
        ads = await add_ads(self.session, ads)
        response_message = {
            "id": ads.ads_id,
            "title": ads.title,
            "description": ads.description,
            "status": "created",
            "owner_id": ads.owner_id
        }
        return web.json_response(response_message)

    async def patch(self):
        """Для исправления объявления."""
        try:
            ads = await get_ads(self.session, self.ads_id)  # Получаем пользователя.
            old_title = ads.title  # Сохраняем старое имя пользователя
            old_description = ads.description  # Сохраняем старое содержимое

            json_data = await self.request.json()  # Извлекаем JSON данные из запроса.
            # if "password" in json_data:  # Если в исправляемых данных присутствует пароль, то...
            #     json_data["password"] = hash_password(json_data["password"])  # ...хешируем пароль перед сохранением.
            for field, value in json_data.items():  # Применяем изменения к объекту пользователя
                setattr(ads, field, value)
            await add_ads(self.session, ads)  # Сохраняем обновленного пользователя в базе данных
            response_message = {
                "id": ads.ads_id,
                "old_title": old_title,
                "old_description": old_description,
                "new_title": ads.title,  # Заголовок объявления.
                "description": ads.description,  # Описание объявления.
                "status": "has been changed"  # Статус изменено.
            }
            return web.json_response(response_message)
        except IntegrityError as e:
            if 'UniqueViolationError' in str(e.orig):  # Проверяем, связана ли ошибка с нарушением уникальности.
                return web.json_response({"error": "A ads with this name already exists."}, status=400)
            else:
                raise  # Перебрасываем другую ошибку, если она возникла

    async def delete(self):
        """Для удаления объявления."""
        ads = await get_ads(self.session, self.ads_id)  # Получаем пользователя.
        await self.session.delete(ads)
        await self.session.commit()
        response_message = {
            "id": ads.ads_id,
            "name": ads.title,
            "status": "delete"
        }
        return web.json_response(response_message)


class AdsUserView(web.View):

    @property
    def session(self) -> Session:
        return self.request.session

    @property
    def user_id(self) -> int:
        try:
            return int(self.request.match_info["user_id"])
        except KeyError:
            return None

    @property
    def ads_id(self) -> int:
        return int(self.request.match_info["ads_id"])

    async def get(self):
        """Для просмотра всех объявлений пользователя."""
        user_id = self.user_id
        if user_id is None:
            return web.json_response({"error": "User ID not found"}, status=404)

        ads_list = await get_all_ads_for_user(self.session, user_id)

        response_data = [
            {
                'ads_id': ad.ads_id,
                'title': ad.title,
                'description': ad.description,
                "owner_id": ad.owner_id
            } for ad in ads_list
        ]

        return web.json_response(response_data)


# Формируем routes с помощью метода Application - add_routes.
app.add_routes([
    web.post('/user', UserView),
    web.get('/user/{user_id:\d+}', UserView),
    web.patch('/user/{user_id:\d+}', UserView),
    web.delete('/user/{user_id:\d+}', UserView),

    web.get('/ads/user/{user_id:\d+}', AdsUserView),

    web.post('/user/{user_id:\d+}/ads', AdsView),
    web.get('/ads/{ads_id:\d+}', AdsView),
    web.patch('/ads/{ads_id:\d+}', AdsView),
    web.delete('/ads/{ads_id:\d+}', AdsView),
])


web.run_app(app)  # Асинхронный run
