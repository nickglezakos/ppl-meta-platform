import os
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://nickadmin:Kodikos%4023@localhost/ppl_db"
)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def print_database_structure():
    inspector = inspect(engine)
    print("Database Tables and Structure:\n")
    for table_name in inspector.get_table_names():
        print(f"Table: {table_name}")
        columns = inspector.get_columns(table_name)
        for column in columns:
            col_name = column['name']
            col_type = column['type']
            nullable = column['nullable']
            default = column.get('default')
            print(f"  - {col_name} ({col_type}), nullable={nullable}, default={default}")
        print()


if __name__ == "__main__":
    print_database_structure()