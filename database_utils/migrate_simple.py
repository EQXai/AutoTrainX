#!/usr/bin/env python3
"""
Simple migration script from SQLite to PostgreSQL without complex dependencies.
"""

import sqlite3
import psycopg2
import json
from datetime import datetime
import sys

def migrate_simple():
    """Simple migration without using the complex factory system."""
    
    print("Starting simple migration...")
    
    # Connect to SQLite
    print("Connecting to SQLite...")
    sqlite_conn = sqlite3.connect('DB/executions.db')
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()
    
    # Connect to PostgreSQL
    print("Connecting to PostgreSQL...")
    pg_conn = psycopg2.connect(
        host="localhost",
        database="autotrainx",
        user="autotrainx",
        password="1234"
    )
    pg_cursor = pg_conn.cursor()
    
    # Create tables in PostgreSQL
    print("Creating tables in PostgreSQL...")
    
    # Create executions table
    pg_cursor.execute("""
        CREATE TABLE IF NOT EXISTS executions (
            job_id VARCHAR(8) PRIMARY KEY,
            status VARCHAR(50) NOT NULL,
            pipeline_mode VARCHAR(20) NOT NULL,
            dataset_name VARCHAR(255) NOT NULL,
            preset VARCHAR(100) NOT NULL,
            total_steps INTEGER,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            duration_seconds FLOAT,
            success BOOLEAN DEFAULT FALSE,
            error_message TEXT,
            output_path TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)
    
    # Create variations table
    pg_cursor.execute("""
        CREATE TABLE IF NOT EXISTS variations (
            job_id VARCHAR(8) PRIMARY KEY,
            status VARCHAR(50) NOT NULL,
            variation_id VARCHAR(100) NOT NULL,
            experiment_name VARCHAR(255) NOT NULL,
            dataset_name VARCHAR(255) NOT NULL,
            preset VARCHAR(100) NOT NULL,
            total_steps INTEGER,
            total_combinations INTEGER NOT NULL,
            varied_parameters JSONB,
            parameter_values JSONB,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            duration_seconds FLOAT,
            success BOOLEAN DEFAULT FALSE,
            error_message TEXT,
            output_path TEXT,
            parent_experiment_id VARCHAR(100),
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)
    
    pg_conn.commit()
    
    # Migrate executions
    print("\nMigrating executions table...")
    sqlite_cursor.execute("SELECT * FROM executions")
    executions = sqlite_cursor.fetchall()
    print(f"Found {len(executions)} executions to migrate")
    
    for row in executions:
        try:
            pg_cursor.execute("""
                INSERT INTO executions (
                    job_id, status, pipeline_mode, dataset_name, preset,
                    total_steps, start_time, end_time, duration_seconds,
                    success, error_message, output_path, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                row['job_id'], row['status'], row['pipeline_mode'],
                row['dataset_name'], row['preset'], row['total_steps'],
                row['start_time'], row['end_time'], row['duration_seconds'],
                bool(row['success']) if row['success'] is not None else None,
                row['error_message'], row['output_path'],
                row['created_at'], row['updated_at']
            ))
            print(f"  ✓ Migrated execution: {row['job_id']}")
        except Exception as e:
            print(f"  ✗ Error migrating execution {row['job_id']}: {e}")
    
    pg_conn.commit()
    
    # Migrate variations
    print("\nMigrating variations table...")
    sqlite_cursor.execute("SELECT * FROM variations")
    variations = sqlite_cursor.fetchall()
    print(f"Found {len(variations)} variations to migrate")
    
    for row in variations:
        try:
            # Parse JSON from TEXT columns
            varied_params = json.loads(row['varied_parameters']) if row['varied_parameters'] else {}
            param_values = json.loads(row['parameter_values']) if row['parameter_values'] else {}
            
            pg_cursor.execute("""
                INSERT INTO variations (
                    job_id, status, variation_id, experiment_name, dataset_name,
                    preset, total_steps, total_combinations, varied_parameters,
                    parameter_values, start_time, end_time, duration_seconds,
                    success, error_message, output_path, parent_experiment_id,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                row['job_id'], row['status'], row['variation_id'],
                row['experiment_name'], row['dataset_name'], row['preset'],
                row['total_steps'], row['total_combinations'],
                json.dumps(varied_params), json.dumps(param_values),
                row['start_time'], row['end_time'], row['duration_seconds'],
                bool(row['success']) if row['success'] is not None else None,
                row['error_message'], row['output_path'],
                row['parent_experiment_id'], row['created_at'], row['updated_at']
            ))
            print(f"  ✓ Migrated variation: {row['job_id']}")
        except Exception as e:
            print(f"  ✗ Error migrating variation {row['job_id']}: {e}")
    
    pg_conn.commit()
    
    # Check other tables
    print("\nChecking for other tables...")
    sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    all_tables = [row[0] for row in sqlite_cursor.fetchall()]
    print(f"Tables in SQLite: {all_tables}")
    
    # Create indexes
    print("\nCreating indexes...")
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_executions_status ON executions(status)",
        "CREATE INDEX IF NOT EXISTS idx_executions_dataset ON executions(dataset_name)",
        "CREATE INDEX IF NOT EXISTS idx_executions_created ON executions(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_variations_status ON variations(status)",
        "CREATE INDEX IF NOT EXISTS idx_variations_experiment ON variations(experiment_name)",
    ]
    
    for idx in indexes:
        try:
            pg_cursor.execute(idx)
            print(f"  ✓ Created index: {idx.split('idx_')[1].split(' ')[0]}")
        except Exception as e:
            print(f"  ✗ Error creating index: {e}")
    
    pg_conn.commit()
    
    # Verify migration
    print("\n" + "="*60)
    print("MIGRATION SUMMARY")
    print("="*60)
    
    # Check PostgreSQL counts
    pg_cursor.execute("SELECT COUNT(*) FROM executions")
    pg_exec_count = pg_cursor.fetchone()[0]
    
    pg_cursor.execute("SELECT COUNT(*) FROM variations")
    pg_var_count = pg_cursor.fetchone()[0]
    
    print(f"\nSQLite -> PostgreSQL:")
    print(f"  Executions: {len(executions)} -> {pg_exec_count}")
    print(f"  Variations: {len(variations)} -> {pg_var_count}")
    
    # Close connections
    sqlite_conn.close()
    pg_conn.close()
    
    print("\n✅ Migration completed!")

if __name__ == "__main__":
    try:
        migrate_simple()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)