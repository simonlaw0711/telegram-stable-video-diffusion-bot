# database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.future import select
from models.db_models import User  # Adjust the import path based on your project structure
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = f"mysql+aiomysql://{os.getenv('MYSQL_USERNAME')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}/{os.getenv('MYSQL_DATABASE')}?charset=utf8mb4"

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()

class DatabaseHandler:
    def __init__(self):
        self.database_url = DATABASE_URL
        self.engine = engine
        self.SessionLocal = AsyncSessionLocal

    async def connect_to_db(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Connected to database and ensured tables are created.")

    async def disconnect_from_db(self):
        await self.engine.dispose()
        print("Disconnected from database.")

    async def update_user_credits(self, username: str, credits_to_add: int):
        async with self.SessionLocal() as session:
            stmt = select(User).where(User.username == username)
            result = await session.execute(stmt)
            user = result.scalars().first()
            if user:
                user.credits += credits_to_add
                await session.commit()
                return True
            else:
                await session.rollback()
                return False
