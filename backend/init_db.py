"""Initialize database with schema and sample data"""
import os
import sys
import time
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/agent_network")

def wait_for_db(max_retries=30):
    """Wait for database to be ready"""
    engine = create_engine(DATABASE_URL)
    
    for i in range(max_retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("✓ Database is ready")
            return engine
        except Exception as e:
            print(f"Waiting for database... ({i+1}/{max_retries})")
            time.sleep(2)
    
    raise Exception("Database not available")

def init_database():
    """Initialize database with schema"""
    print("Initializing database...")
    
    engine = wait_for_db()
    
    # Read schema file
    schema_path = os.path.join(os.path.dirname(__file__), '..', 'sql', 'schema.sql')
    
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    
    # Execute schema
    with engine.connect() as conn:
        # Execute in transaction
        trans = conn.begin()
        try:
            # Split by statement (simple approach)
            statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
            
            for statement in statements:
                if statement and not statement.startswith('/*'):
                    try:
                        conn.execute(text(statement))
                    except Exception as e:
                        # Ignore errors for already existing objects
                        if 'already exists' not in str(e):
                            print(f"Warning: {e}")
            
            trans.commit()
            print("✓ Database schema initialized")
        except Exception as e:
            trans.rollback()
            print(f"Error initializing database: {e}")
            raise

def add_sample_data():
    """Add sample data if requested"""
    print("Adding sample data...")
    
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Check if data already exists
        result = conn.execute(text("SELECT COUNT(*) FROM users"))
        count = result.scalar()
        
        if count > 0:
            print("✓ Sample data already exists")
            return
        
        # Sample data is already in schema.sql
        print("✓ Sample data loaded")

if __name__ == "__main__":
    reset = "--reset" in sys.argv
    
    if reset:
        print("Resetting database...")
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
            conn.commit()
    
    init_database()
    add_sample_data()
    print("\n✓ Database initialization complete!")
