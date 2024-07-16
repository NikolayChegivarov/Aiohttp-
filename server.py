from aiohttp import web
import json
from models import Base, engine, Session
from sqlalchemy.exc import InvalidRequestError

app = web.Application()   # Создаем экземпляр класса web


async def orm_context(app):
    print("start")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
    print("SHUTDOWN")

@web.middleware
async def session_middleware(request: web.Request, handler):
    async with Session() as session:
        request.session = session
        response = await (request)
        return response


app.cleanup_ctx.append(orm_context)
app.middlewares.append(session_middleware)


async def get_http_error(error_class, msg):
    return error_class(
        text=json.dump({"error": msg}),
        content_type='aplication/json'
    )


async  def add_user(session: Session, user: User):
    try
        session.add(user)
        await sessin.commit()
    except InvalidRequestError
        raise get_http_error(web.HTTPConflict, 'user already axist')


class UserView(web.viev):
    async def get(self):
        pass
    async def post(self):
        pass
    async def patch(self):
        pass
    async def delete(self):
        pass

# Формируем routes с помощью метода Application - add_routes
# То есть привязываем url для вьюшки.
app.add_routes([
    web.post('/user', UserView),
    web.get('/user/{user_id:\d+}', UserView),
    web.patch('/user/{user_id:\d+}', UserView),
    web.delete('/user/{user_id:\d+}', UserView),
])  # url для вьюшки.

web.run_app(app)  # Асинхронный run
