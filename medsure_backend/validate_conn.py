import asyncio, json, time, sys, os
sys.path.insert(0, ".")
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgrespassword@localhost:5432/medsure_db"

async def main():
    import asyncpg
    conn = await asyncpg.connect(
        "postgresql://postgres:postgrespassword@localhost:5432/medsure_db"
    )
    print("=== DATABASE CONNECTIVITY ===")
    row = await conn.fetchrow("SELECT version()")
    print("PG version:", row["version"][:60])

    print("\n=== TABLE COUNTS ===")
    for tbl in ["medicines","medicine_variants","manufacturers","medicine_codes"]:
        n = await conn.fetchval(f"SELECT COUNT(*) FROM {tbl}")
        print(f"  {tbl}: {n:,}")

    await conn.close()
    print("\n[OK] Connection successful")

asyncio.run(main())
