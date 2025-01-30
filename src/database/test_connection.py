import asyncio
from sqlalchemy import text
from config import get_db

async def test_connection():
    """Test database connection and list existing databases"""
    try:
        async with get_db() as db:
            # Test connection by getting PostgreSQL version
            result = await db.execute(text('SELECT version()'))
            version = result.scalar()
            print(f"\nPostgreSQL Version:\n{version}\n")
            
            # List all databases
            result = await db.execute(
                text("""
                    SELECT datname 
                    FROM pg_database 
                    WHERE datistemplate = false
                    ORDER BY datname;
                """)
            )
            databases = result.scalars().all()
            print("Available Databases:")
            for db_name in databases:
                print(f"- {db_name}")
            
            # Get current database size
            result = await db.execute(
                text("""
                    SELECT 
                        pg_size_pretty(pg_database_size(current_database())) as size,
                        current_database() as db_name;
                """)
            )
            size, db_name = result.first()
            print(f"\nCurrent Database: {db_name}")
            print(f"Size: {size}")
            
            # List schemas in current database
            result = await db.execute(
                text("""
                    SELECT schema_name 
                    FROM information_schema.schemata 
                    WHERE schema_name NOT IN ('information_schema', 'pg_catalog')
                    ORDER BY schema_name;
                """)
            )
            schemas = result.scalars().all()
            print("\nAvailable Schemas:")
            for schema in schemas:
                print(f"- {schema}")
            
            # List tables in public schema
            result = await db.execute(
                text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name;
                """)
            )
            tables = result.scalars().all()
            print("\nTables in public schema:")
            for table in tables:
                print(f"- {table}")

    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(test_connection()) 