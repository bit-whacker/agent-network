"""Database connection and utilities"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/agent_network")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def execute_query(query: str, params: dict = None):
    """Execute a query and return results"""
    with get_db() as db:
        result = db.execute(text(query), params or {})
        if result.returns_rows:
            return result.mappings().all()
        return None

def execute_function(func_name: str, *args):
    """Execute a PostgreSQL function"""
    placeholders = ', '.join([f':arg{i}' for i in range(len(args))])
    query = f"SELECT {func_name}({placeholders}) as result"
    params = {f'arg{i}': arg for i, arg in enumerate(args)}
    
    with get_db() as db:
        result = db.execute(text(query), params)
        row = result.fetchone()
        return row[0] if row else None
