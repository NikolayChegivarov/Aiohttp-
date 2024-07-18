from aiohttp import web  # Aсинхронная клиент-серверная HTTP-библиотека для asyncio и Python
import json
from models import Base, engine, Session, User
from sqlalchemy.exc import InvalidRequestError
import bcrypt  # Для безопасного хеширования паролей.

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
    user = await session.get(User, user_id)
    if user is None:
        raise get_http_error(web.HTTPFound, 'user already axist')
    return user


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
        json_data["password"] = hash_password(
            json_data["password"])  # Хеширование пароля перед сохранением пользователя
        user = User(**json_data)  # Создание объекта User с данными из JSON
        user = await add_user(self.session, user)  # Асинхронная добавление пользователя в базу данных
        return web.json_response({"id": user.id})  # Возвращение ответа с ID созданного пользователя

    async def patch(self):
        user = await get_user(self.session, self.user_id)  # Получаем пользователя.
        json_data = await self.request.json()  # Извлекаем JSON данные из запроса.
        if "password" in json_data:  # Если в исправляемых данных присутствует пароль то..
            json_data["password"] = hash_password(json_data["password"])  # ..хешируем пароль перед сохранением.
        for field, value in json_data.items():  # Применяем изменения к объекту пользователя
            setattr(user, field, value)
        await add_user(self.session, user)  # Сохраняем обновленного пользователя в базе данных
        return web.json_response({"id": user.id})  # Возвращаем ответ с идентификатором обновленного пользователя.

    async def delete(self):
        """Для удаления пользователя."""
        user = await get_user(self.session, self.user_id)  # Получаем пользователя.
        await self.session.delite(user)
        await self.session.commit()
        return web.json_response({'status': 'delite'})


# Формируем routes с помощью метода Application - add_routes
# То есть привязываем url для вьюшки.
app.add_routes([
    web.post('/user', UserView),
    web.get('/user/{user_id:\d+}', UserView),
    web.patch('/user/{user_id:\d+}', UserView),
    web.delete('/user/{user_id:\d+}', UserView),
])  # url для вьюшки.

web.run_app(app)  # Асинхронный run
