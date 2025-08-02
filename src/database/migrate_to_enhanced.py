"""Migration script to upgrade to enhanced database manager."""

import logging
import argparse
from pathlib import Path
from typing import Optional

from sqlalchemy import text

from .manager import DatabaseManager
from .enhanced_manager import EnhancedDatabaseManager
from .schema_improvements import SchemaOptimizer

logger = logging.getLogger(__name__)


class DatabaseMigrator:
    """Migrate from standard to enhanced database manager."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize migrator.
        
        Args:
            db_path: Path to database file
        """
        self.db_path = db_path
        self.old_manager = DatabaseManager(db_path)
        self.new_manager = None
    
    def migrate(self, backup: bool = True) -> bool:
        """Perform migration to enhanced database.
        
        Args:
            backup: Whether to create backup before migration
            
        Returns:
            True if migration successful
        """
        try:
            logger.info("Starting database migration to enhanced version")
            
            # Step 1: Create backup if requested
            if backup:
                self._create_backup()
            
            # Step 2: Initialize enhanced manager
            self.new_manager = EnhancedDatabaseManager(self.db_path)
            
            # Step 3: Apply schema optimizations
            self._apply_schema_optimizations()
            
            # Step 4: Build caches
            self._build_caches()
            
            # Step 5: Verify data integrity
            if not self._verify_data_integrity():
                logger.error("Data integrity check failed")
                return False
            
            # Step 6: Run optimization
            self._run_optimizations()
            
            logger.info("Database migration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False
    
    def _create_backup(self):
        """Create database backup."""
        import shutil
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.db_path.with_suffix(f'.backup_{timestamp}.db')
        
        logger.info(f"Creating backup: {backup_path}")
        shutil.copy2(self.db_path, backup_path)
        
        # Also backup WAL file if exists
        wal_path = self.db_path.with_suffix('.db-wal')
        if wal_path.exists():
            wal_backup = backup_path.with_suffix('.db-wal')
            shutil.copy2(wal_path, wal_backup)
    
    def _apply_schema_optimizations(self):
        """Apply all schema optimizations."""
        logger.info("Applying schema optimizations")
        
        with self.new_manager.pool_manager.engine.connect() as conn:
            # Create new indexes
            SchemaOptimizer.apply_optimizations(self.new_manager.pool_manager.engine)
            
            # Create materialized view
            SchemaOptimizer.create_materialized_view(self.new_manager.pool_manager.engine)
            
            # Update statistics
            conn.execute(text("ANALYZE;"))
            conn.commit()
    
    def _build_caches(self):
        """Build initial caches."""
        logger.info("Building caches")
        
        # Refresh job summary cache
        self.new_manager.refresh_job_cache()
        
        # Warm up connection pool
        for _ in range(5):
            with self.new_manager.get_session() as session:
                session.execute(text("SELECT 1"))
    
    def _verify_data_integrity(self) -> bool:
        """Verify data integrity after migration."""
        logger.info("Verifying data integrity")
        
        try:
            # Compare record counts
            with self.old_manager.get_session() as old_session:
                old_exec_count = old_session.query(Execution).count()
                old_var_count = old_session.query(Variation).count()
            
            with self.new_manager.get_session() as new_session:
                new_exec_count = new_session.query(Execution).count()
                new_var_count = new_session.query(Variation).count()
            
            if old_exec_count != new_exec_count:
                logger.error(f"Execution count mismatch: {old_exec_count} vs {new_exec_count}")
                return False
            
            if old_var_count != new_var_count:
                logger.error(f"Variation count mismatch: {old_var_count} vs {new_var_count}")
                return False
            
            logger.info(f"Data integrity verified: {old_exec_count} executions, {old_var_count} variations")
            return True
            
        except Exception as e:
            logger.error(f"Data integrity check failed: {e}")
            return False
    
    def _run_optimizations(self):
        """Run final optimizations."""
        logger.info("Running final optimizations")
        
        # Vacuum database
        self.new_manager.vacuum_database()
        
        # Run initial health check
        from .monitoring import DatabaseHealthMonitor
        monitor = DatabaseHealthMonitor(self.new_manager)
        health = monitor.check_health()
        
        logger.info(f"Health check status: {health['status']}")
        if health['warnings']:
            logger.warning(f"Health warnings: {health['warnings']}")


def main():
    """Command-line interface for migration."""
    parser = argparse.ArgumentParser(description="Migrate to enhanced database")
    parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to database file"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip backup creation"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run migration
    migrator = DatabaseMigrator(args.db_path)
    success = migrator.migrate(backup=not args.no_backup)
    
    if success:
        print("Migration completed successfully!")
        print("\nTo use the enhanced database manager in your code:")
        print("  from src.database.enhanced_manager import EnhancedDatabaseManager")
        print("  db_manager = EnhancedDatabaseManager()")
    else:
        print("Migration failed. Check logs for details.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())