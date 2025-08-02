#!/usr/bin/env python3
"""
Migration script from SQLite to PostgreSQL for AutoTrainX database.

Usage:
    python migrate_to_postgresql.py --source sqlite.db --target postgresql://user:pass@host/db
    
    Or with environment variables:
    export SOURCE_DB_PATH=/path/to/sqlite.db
    export TARGET_DB_URL=postgresql://user:pass@host/db
    python migrate_to_postgresql.py
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, Session

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.models_v2 import Base, Execution, Variation, JobSummaryCache, ModelPath, Model
from src.database.factory import DatabaseFactory, DatabaseConfig

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DatabaseMigrator:
    """Handles migration from SQLite to PostgreSQL."""
    
    def __init__(self, source_path: str, target_url: str):
        """Initialize migrator with source and target databases.
        
        Args:
            source_path: Path to SQLite database
            target_url: PostgreSQL connection URL
        """
        print(f"Initializing DatabaseMigrator...")
        print(f"  Source: {source_path}")
        print(f"  Target: {target_url[:30]}...")
        
        # Create source engine (SQLite)
        print("Creating SQLite connection...")
        self.source_config = DatabaseConfig(
            db_type='sqlite',
            db_path=Path(source_path)
        )
        self.source_engine = DatabaseFactory.create_engine(self.source_config)
        self.SourceSession = sessionmaker(bind=self.source_engine)
        print("SQLite connection created successfully")
        
        # Create target engine (PostgreSQL)
        print("Creating PostgreSQL connection...")
        self.target_config = DatabaseConfig(
            db_type='postgresql',
            db_url=target_url
        )
        self.target_engine = DatabaseFactory.create_engine(self.target_config)
        self.TargetSession = sessionmaker(bind=self.target_engine)
        print("PostgreSQL connection created successfully")
        
        # Migration stats
        self.stats = {
            'executions': {'total': 0, 'migrated': 0, 'errors': 0},
            'variations': {'total': 0, 'migrated': 0, 'errors': 0},
            'job_summary_cache': {'total': 0, 'migrated': 0, 'errors': 0},
            'model_paths': {'total': 0, 'migrated': 0, 'errors': 0},
            'models': {'total': 0, 'migrated': 0, 'errors': 0},
        }
    
    def verify_source(self) -> bool:
        """Verify source database is accessible and has expected schema.
        
        Returns:
            True if source is valid
        """
        try:
            inspector = inspect(self.source_engine)
            tables = inspector.get_table_names()
            
            expected_tables = ['executions', 'variations']
            for table in expected_tables:
                if table not in tables:
                    logger.error(f"Source database missing required table: {table}")
                    return False
            
            logger.info(f"Source database verified. Tables: {', '.join(tables)}")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying source database: {e}")
            return False
    
    def prepare_target(self, drop_existing: bool = False) -> bool:
        """Prepare target database schema.
        
        Args:
            drop_existing: Drop existing tables before creating
            
        Returns:
            True if successful
        """
        try:
            if drop_existing:
                logger.warning("Dropping existing tables in target database")
                Base.metadata.drop_all(self.target_engine)
            
            logger.info("Creating schema in target database")
            Base.metadata.create_all(self.target_engine)
            
            # Apply PostgreSQL optimizations
            from src.database.schema_improvements_v2 import SchemaOptimizer
            SchemaOptimizer.apply_optimizations(self.target_engine)
            
            return True
            
        except Exception as e:
            logger.error(f"Error preparing target database: {e}")
            return False
    
    def migrate_executions(self, batch_size: int = 1000) -> int:
        """Migrate executions table.
        
        Args:
            batch_size: Number of records to process at once
            
        Returns:
            Number of records migrated
        """
        logger.info("Migrating executions table...")
        
        with self.SourceSession() as source_session:
            with self.TargetSession() as target_session:
                # Get total count
                total = source_session.query(Execution).count()
                self.stats['executions']['total'] = total
                logger.info(f"Found {total} executions to migrate")
                
                # Process in batches
                offset = 0
                while offset < total:
                    try:
                        # Fetch batch from source
                        batch = source_session.query(Execution)\
                            .order_by(Execution.created_at)\
                            .offset(offset)\
                            .limit(batch_size)\
                            .all()
                        
                        # Insert into target
                        for execution in batch:
                            # Create new instance to avoid session conflicts
                            new_exec = Execution(
                                job_id=execution.job_id,
                                status=execution.status,
                                pipeline_mode=execution.pipeline_mode,
                                dataset_name=execution.dataset_name,
                                preset=execution.preset,
                                total_steps=execution.total_steps,
                                start_time=execution.start_time,
                                end_time=execution.end_time,
                                duration_seconds=execution.duration_seconds,
                                success=execution.success,
                                error_message=execution.error_message,
                                output_path=execution.output_path,
                                created_at=execution.created_at,
                                updated_at=execution.updated_at
                            )
                            target_session.add(new_exec)
                        
                        target_session.commit()
                        self.stats['executions']['migrated'] += len(batch)
                        
                        logger.info(f"Migrated {offset + len(batch)}/{total} executions")
                        offset += batch_size
                        
                    except Exception as e:
                        logger.error(f"Error migrating executions batch at offset {offset}: {e}")
                        self.stats['executions']['errors'] += batch_size
                        target_session.rollback()
                        offset += batch_size
        
        return self.stats['executions']['migrated']
    
    def migrate_variations(self, batch_size: int = 1000) -> int:
        """Migrate variations table.
        
        Args:
            batch_size: Number of records to process at once
            
        Returns:
            Number of records migrated
        """
        logger.info("Migrating variations table...")
        
        with self.SourceSession() as source_session:
            with self.TargetSession() as target_session:
                # Get total count
                total = source_session.query(Variation).count()
                self.stats['variations']['total'] = total
                logger.info(f"Found {total} variations to migrate")
                
                # Process in batches
                offset = 0
                while offset < total:
                    try:
                        # Fetch batch from source
                        batch = source_session.query(Variation)\
                            .order_by(Variation.created_at)\
                            .offset(offset)\
                            .limit(batch_size)\
                            .all()
                        
                        # Insert into target
                        for variation in batch:
                            # Parse JSON if stored as string
                            varied_params = variation.varied_parameters
                            if isinstance(varied_params, str):
                                varied_params = json.loads(varied_params) if varied_params else {}
                            
                            param_values = variation.parameter_values
                            if isinstance(param_values, str):
                                param_values = json.loads(param_values) if param_values else {}
                            
                            # Create new instance
                            new_var = Variation(
                                job_id=variation.job_id,
                                status=variation.status,
                                variation_id=variation.variation_id,
                                experiment_name=variation.experiment_name,
                                dataset_name=variation.dataset_name,
                                preset=variation.preset,
                                total_steps=variation.total_steps,
                                total_combinations=variation.total_combinations,
                                varied_parameters=varied_params,
                                parameter_values=param_values,
                                start_time=variation.start_time,
                                end_time=variation.end_time,
                                duration_seconds=variation.duration_seconds,
                                success=variation.success,
                                error_message=variation.error_message,
                                output_path=variation.output_path,
                                parent_experiment_id=variation.parent_experiment_id,
                                created_at=variation.created_at,
                                updated_at=variation.updated_at
                            )
                            target_session.add(new_var)
                        
                        target_session.commit()
                        self.stats['variations']['migrated'] += len(batch)
                        
                        logger.info(f"Migrated {offset + len(batch)}/{total} variations")
                        offset += batch_size
                        
                    except Exception as e:
                        logger.error(f"Error migrating variations batch at offset {offset}: {e}")
                        self.stats['variations']['errors'] += batch_size
                        target_session.rollback()
                        offset += batch_size
        
        return self.stats['variations']['migrated']
    
    def migrate_cache_tables(self) -> bool:
        """Migrate cache and auxiliary tables if they exist.
        
        Returns:
            True if successful
        """
        # Check if tables exist in source
        inspector = inspect(self.source_engine)
        tables = inspector.get_table_names()
        
        # Migrate job_summary_cache if exists
        if 'job_summary_cache' in tables:
            logger.info("Migrating job_summary_cache table...")
            try:
                with self.source_engine.connect() as source_conn:
                    # Read all cache entries
                    result = source_conn.execute(text("SELECT * FROM job_summary_cache"))
                    rows = result.fetchall()
                    self.stats['job_summary_cache']['total'] = len(rows)
                    
                    with self.target_engine.connect() as target_conn:
                        for row in rows:
                            target_conn.execute(text("""
                                INSERT INTO job_summary_cache 
                                (job_id, job_type, status, dataset_name, preset, 
                                 start_time, duration_seconds, success, last_updated)
                                VALUES (:job_id, :job_type, :status, :dataset_name, :preset,
                                        :start_time, :duration_seconds, :success, :last_updated)
                            """), dict(row))
                            self.stats['job_summary_cache']['migrated'] += 1
                        
                        target_conn.commit()
                
                logger.info(f"Migrated {self.stats['job_summary_cache']['migrated']} cache entries")
                
            except Exception as e:
                logger.error(f"Error migrating cache table: {e}")
                self.stats['job_summary_cache']['errors'] += 1
        
        # Migrate model_paths and models if they exist
        if 'model_paths' in tables:
            self._migrate_model_tables()
        
        return True
    
    def _migrate_model_tables(self):
        """Migrate model_paths and models tables."""
        logger.info("Migrating model tables...")
        
        with self.SourceSession() as source_session:
            with self.TargetSession() as target_session:
                # Migrate model_paths
                model_paths = source_session.query(ModelPath).all()
                self.stats['model_paths']['total'] = len(model_paths)
                
                for path in model_paths:
                    new_path = ModelPath(
                        id=path.id,
                        path=path.path,
                        added_at=path.added_at,
                        last_scan=path.last_scan,
                        model_count=path.model_count
                    )
                    target_session.add(new_path)
                    self.stats['model_paths']['migrated'] += 1
                
                target_session.commit()
                
                # Migrate models
                models = source_session.query(Model).all()
                self.stats['models']['total'] = len(models)
                
                for model in models:
                    # Parse JSON if needed
                    preview_images = model.preview_images
                    if isinstance(preview_images, str):
                        preview_images = json.loads(preview_images) if preview_images else []
                    
                    # Handle metadata - check both old and new column names
                    metadata = getattr(model, 'model_metadata', None) or getattr(model, 'metadata', None)
                    if isinstance(metadata, str):
                        metadata = json.loads(metadata) if metadata else {}
                    
                    new_model = Model(
                        id=model.id,
                        name=model.name,
                        path=model.path,
                        type=model.type,
                        size=model.size,
                        created_at=model.created_at,
                        modified_at=model.modified_at,
                        has_preview=model.has_preview,
                        preview_images=preview_images,
                        model_metadata=metadata,
                        path_id=model.path_id
                    )
                    target_session.add(new_model)
                    self.stats['models']['migrated'] += 1
                
                target_session.commit()
    
    def verify_migration(self) -> bool:
        """Verify migration was successful by comparing counts.
        
        Returns:
            True if verification passed
        """
        logger.info("Verifying migration...")
        
        with self.TargetSession() as session:
            # Check counts
            exec_count = session.query(Execution).count()
            var_count = session.query(Variation).count()
            
            logger.info(f"Target database has {exec_count} executions, {var_count} variations")
            
            # Compare with source
            success = True
            if exec_count != self.stats['executions']['migrated']:
                logger.error(f"Execution count mismatch: {exec_count} != {self.stats['executions']['migrated']}")
                success = False
            
            if var_count != self.stats['variations']['migrated']:
                logger.error(f"Variation count mismatch: {var_count} != {self.stats['variations']['migrated']}")
                success = False
            
            return success
    
    def print_summary(self):
        """Print migration summary."""
        print("\n" + "="*60)
        print("MIGRATION SUMMARY")
        print("="*60)
        
        for table, stats in self.stats.items():
            if stats['total'] > 0:
                success_rate = (stats['migrated'] / stats['total']) * 100 if stats['total'] > 0 else 0
                print(f"\n{table}:")
                print(f"  Total: {stats['total']}")
                print(f"  Migrated: {stats['migrated']}")
                print(f"  Errors: {stats['errors']}")
                print(f"  Success Rate: {success_rate:.1f}%")
        
        print("\n" + "="*60)
    
    def migrate(self, drop_existing: bool = False) -> bool:
        """Perform the complete migration.
        
        Args:
            drop_existing: Drop existing tables in target
            
        Returns:
            True if successful
        """
        logger.info("Starting database migration from SQLite to PostgreSQL")
        
        # Verify source
        if not self.verify_source():
            return False
        
        # Prepare target
        if not self.prepare_target(drop_existing):
            return False
        
        # Migrate data
        self.migrate_executions()
        self.migrate_variations()
        self.migrate_cache_tables()
        
        # Verify
        success = self.verify_migration()
        
        # Print summary
        self.print_summary()
        
        return success


def main():
    """Main entry point."""
    print("Starting migration script...")
    
    parser = argparse.ArgumentParser(description="Migrate AutoTrainX database from SQLite to PostgreSQL")
    parser.add_argument('--source', help='Source SQLite database path', 
                       default=os.environ.get('SOURCE_DB_PATH'))
    parser.add_argument('--target', help='Target PostgreSQL URL',
                       default=os.environ.get('TARGET_DB_URL'))
    parser.add_argument('--drop-existing', action='store_true',
                       help='Drop existing tables in target database')
    parser.add_argument('--batch-size', type=int, default=1000,
                       help='Batch size for migration (default: 1000)')
    
    args = parser.parse_args()
    print(f"Arguments parsed: source={args.source}, target={args.target[:30]}...")
    
    # Validate arguments
    if not args.source:
        parser.error("Source database path required (--source or SOURCE_DB_PATH env var)")
    
    if not args.target:
        parser.error("Target database URL required (--target or TARGET_DB_URL env var)")
    
    if not Path(args.source).exists():
        parser.error(f"Source database not found: {args.source}")
    
    print("Creating migrator...")
    try:
        # Perform migration
        migrator = DatabaseMigrator(args.source, args.target)
        print("Migrator created, starting migration...")
        success = migrator.migrate(drop_existing=args.drop_existing)
        
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()