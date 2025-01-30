import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from .config import DATABASE_URL
from .models import Base

async def init_db():
    """Initialize the database by creating all tables"""
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_db()) 