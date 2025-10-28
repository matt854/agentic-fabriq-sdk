#!/usr/bin/env python3
"""
Database Migration: Add user token columns and registered_applications table
"""

import os
from sqlalchemy import create_engine, text, inspect

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+psycopg2://user:password@localhost:5432/db')

def migrate():
    print("🔧 Database Migration: User Tokens + Registered Applications")
    print("=" * 70)
    
    sync_db_url = DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql+psycopg2://')
    engine = create_engine(sync_db_url)
    
    with engine.connect() as connection:
        print("\n✅ Connected to database")
        
        inspector = inspect(connection)
        
        # Part 1: Add user token columns to tool_credentials
        print("\n📋 Part 1: Checking tool_credentials table...")
        
        if 'tool_credentials' in inspector.get_table_names():
            columns = inspector.get_columns('tool_credentials')
            column_names = [col['name'] for col in columns]
            
            new_columns = {
                'user_access_token': 'TEXT',
                'user_refresh_token': 'TEXT',
                'user_token_expiry': 'TIMESTAMP',
                'user_scopes': 'JSON',
                'user_id_slack': 'VARCHAR',
            }
            
            added_count = 0
            for col_name, col_type in new_columns.items():
                if col_name not in column_names:
                    print(f"   Adding column: {col_name}")
                    connection.execute(text(f"ALTER TABLE tool_credentials ADD COLUMN {col_name} {col_type} NULL"))
                    added_count += 1
            
            if added_count > 0:
                connection.commit()
                print(f"\n   ✅ Added {added_count} new column(s)")
            else:
                print(f"\n   ✅ All columns already exist")
        
        # Part 2: Create registered_applications table
        print("\n📋 Part 2: Checking registered_applications table...")
        
        if 'registered_applications' not in inspector.get_table_names():
            print("   Creating table...")
            
            create_table_sql = """
            CREATE TABLE registered_applications (
                id VARCHAR PRIMARY KEY,
                app_id VARCHAR NOT NULL UNIQUE,
                secret_key VARCHAR NOT NULL,
                user_id VARCHAR NOT NULL,
                tenant_id VARCHAR NOT NULL,
                tool_connections JSON DEFAULT '{}'::json NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
            """
            connection.execute(text(create_table_sql))
            
            # Create indexes
            connection.execute(text("CREATE INDEX ix_registered_applications_id ON registered_applications (id)"))
            connection.execute(text("CREATE UNIQUE INDEX ix_registered_applications_app_id ON registered_applications (app_id)"))
            connection.execute(text("CREATE INDEX ix_registered_applications_user_id ON registered_applications (user_id)"))
            connection.execute(text("CREATE INDEX ix_registered_applications_tenant_id ON registered_applications (tenant_id)"))
            
            connection.commit()
            print("   ✅ Table created")
        else:
            print("   ✅ Table already exists")
        
        print("\n✅ Migration complete!")
    
    engine.dispose()

if __name__ == "__main__":
    migrate()
