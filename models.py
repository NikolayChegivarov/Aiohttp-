import datetime
from sqlalchemy import Integer, String, DateTime, func, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship
import os

# Получаем переменные окружения для настройки подключения к PostgreSQL.
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
print(f"получаем переменные окружения? - {POSTGRES_PORT}")

# Создаем строку подключения (DSN) для SQLAlchemy с использованием переменных окружения.
engine = create_async_engine(f"postgresql+psycopg2://"
                             f"{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
                             f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")

Session = async_sessionmaker(bind=engine, )


# Формируем базовый класс.
class Base(DeclarativeBase,AsyncAttrs):
    pass


# Определяем модели.
class Ads(Base):
    __tablename__ = "app_ads"

    ads_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(384), nullable=False)  # Описание.
    registration_time: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey('app_users.id'), nullable=False)
    owner: Mapped['User'] = relationship('User', back_populates='ads')

    @property
    def json(self):
        return {
            "id": self.ads_id,  # Corrected from 'self.id'
            "title": self.title,
            "description": self.description,
            "registration_time": self.registration_time.isoformat(),
            "owner": self.owner_id
        }


class User(Base):
    __tablename__ = "app_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(72), nullable=False)
    registration_time: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

    ads: Mapped[list['Ads']] = relationship('Ads', back_populates='owner')

    # для создания специальных методов, которые можно вызывать как атрибуты объекта, а не как обычные методы
    @property
    def json(self):
        return {
            "id": self.id,
            "name": self.name,
            "registration_time": self.registration_time.isoformat()
        }

