import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionLocal
from sqlalchemy import text

async def list_tables():
    async with AsyncSessionLocal() as session:
        res = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
        tables = [r[0] for r in res.fetchall()]
        print('Tables:', tables)
        for t in tables:
            try:
                cnt = (await session.execute(text(f'SELECT count(*) FROM "{t}";'))).scalar()
                print(f'  {t}: {cnt} rows')
            except Exception as e:
                print(f'  {t}: error {e}')

if __name__ == '__main__':
    asyncio.run(list_tables())
