"""Workspace structure setup and validation utilities."""

import os
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class WorkspaceSetup:
    """Manages the workspace directory structure for AutoTrainX."""
    
    # Required workspace directories
    REQUIRED_DIRS = [
        "workspace",
        "workspace/input",
        "workspace/output",
        "workspace/Presets",
        "workspace/variations",
        "models",
        "Presets/Base",
        "Presets/Custom",
        "logs"
    ]
    
    # Optional directories that may be created during runtime
    OPTIONAL_DIRS = [
        "workspace/temp",
        "workspace/cache",
        "sd-scripts"
    ]
    
    @classmethod
    def validate_workspace(cls, base_path: str) -> Dict[str, Any]:
        """
        Validate the workspace structure.
        
        Args:
            base_path: Base path of the AutoTrainX project
            
        Returns:
            Dictionary with validation results
        """
        base = Path(base_path)
        results = {
            "valid": True,
            "missing_required": [],
            "missing_optional": [],
            "existing_dirs": [],
            "errors": []
        }
        
        # Check required directories
        for dir_path in cls.REQUIRED_DIRS:
            full_path = base / dir_path
            if full_path.exists():
                results["existing_dirs"].append(str(dir_path))
            else:
                results["missing_required"].append(str(dir_path))
                results["valid"] = False
                
        # Check optional directories
        for dir_path in cls.OPTIONAL_DIRS:
            full_path = base / dir_path
            if not full_path.exists():
                results["missing_optional"].append(str(dir_path))
                
        return results
        
    @classmethod
    def setup_workspace(cls, base_path: str, create_optional: bool = False) -> bool:
        """
        Set up the workspace directory structure.
        
        Args:
            base_path: Base path of the AutoTrainX project
            create_optional: Whether to create optional directories
            
        Returns:
            True if successful, False otherwise
        """
        base = Path(base_path)
        
        try:
            # Create required directories
            for dir_path in cls.REQUIRED_DIRS:
                full_path = base / dir_path
                if not full_path.exists():
                    full_path.mkdir(parents=True, exist_ok=True)
                    logger.debug(f"Created directory: {full_path}")
                    
            # Create optional directories if requested
            if create_optional:
                for dir_path in cls.OPTIONAL_DIRS:
                    full_path = base / dir_path
                    if not full_path.exists():
                        full_path.mkdir(parents=True, exist_ok=True)
                        logger.debug(f"Created optional directory: {full_path}")
                        
            # Create .gitkeep files in empty directories
            cls._create_gitkeep_files(base)
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting up workspace: {e}")
            return False
            
    @classmethod
    def _create_gitkeep_files(cls, base_path: Path) -> None:
        """Create .gitkeep files in empty directories to preserve structure in git."""
        empty_dirs = [
            "workspace/input",
            "workspace/output",
            "workspace/Presets",
            "workspace/variations",
            "workspace/temp",
            "workspace/cache",
            "models",
            "logs"
        ]
        
        for dir_path in empty_dirs:
            full_path = base_path / dir_path
            if full_path.exists() and full_path.is_dir():
                gitkeep = full_path / ".gitkeep"
                if not gitkeep.exists() and not any(full_path.iterdir()):
                    gitkeep.touch()
                    logger.debug(f"Created .gitkeep in: {full_path}")
                    
    @classmethod
    def get_workspace_info(cls, base_path: str) -> Dict[str, Any]:
        """
        Get information about the workspace.
        
        Args:
            base_path: Base path of the AutoTrainX project
            
        Returns:
            Dictionary with workspace information
        """
        base = Path(base_path)
        info = {
            "base_path": str(base),
            "directories": {},
            "statistics": {
                "total_input_datasets": 0,
                "total_output_datasets": 0,
                "total_presets": 0,
                "total_variations": 0,
                "total_models": 0,
                "total_logs": 0
            }
        }
        
        # Check each directory
        for dir_path in cls.REQUIRED_DIRS + cls.OPTIONAL_DIRS:
            full_path = base / dir_path
            dir_info = {
                "exists": full_path.exists(),
                "path": str(full_path),
                "items": 0
            }
            
            if full_path.exists() and full_path.is_dir():
                # Count items (excluding .gitkeep)
                items = [item for item in full_path.iterdir() if item.name != '.gitkeep']
                dir_info["items"] = len(items)
                
                # Update statistics
                if dir_path == "workspace/input":
                    info["statistics"]["total_input_datasets"] = len([d for d in items if d.is_dir()])
                elif dir_path == "workspace/output":
                    info["statistics"]["total_output_datasets"] = len([d for d in items if d.is_dir()])
                elif dir_path == "workspace/Presets":
                    info["statistics"]["total_presets"] = len([d for d in items if d.is_dir()])
                elif dir_path == "workspace/variations":
                    info["statistics"]["total_variations"] = len([d for d in items if d.is_dir()])
                elif dir_path == "models":
                    info["statistics"]["total_models"] = len(items)
                elif dir_path == "logs":
                    info["statistics"]["total_logs"] = len([f for f in items if f.is_file()])
                    
            info["directories"][dir_path] = dir_info
            
        return info
        
    @classmethod
    def reorganize_workspace(cls, base_path: str, dry_run: bool = True) -> Dict[str, List[str]]:
        """
        Reorganize workspace to match expected structure.
        
        This method carefully moves files to their correct locations
        while preserving data integrity.
        
        Args:
            base_path: Base path of the AutoTrainX project
            dry_run: If True, only report what would be done
            
        Returns:
            Dictionary with reorganization actions
        """
        base = Path(base_path)
        actions = {
            "moves": [],
            "creates": [],
            "warnings": []
        }
        
        # Check for misplaced files and directories
        # Common patterns to look for:
        patterns = [
            # Datasets in root instead of workspace/input
            ("*.jpg", "workspace/input"),
            ("*.png", "workspace/input"),
            ("*.webp", "workspace/input"),
            # Configs in root instead of workspace/Presets
            ("*_config.toml", "workspace/Presets"),
            # Models in root instead of models/
            ("*.safetensors", "models"),
            ("*.ckpt", "models"),
        ]
        
        for pattern, target_dir in patterns:
            for file_path in base.glob(pattern):
                if file_path.is_file():
                    target_path = base / target_dir / file_path.name
                    actions["moves"].append(f"{file_path} -> {target_path}")
                    
                    if not dry_run:
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        file_path.rename(target_path)
                        logger.info(f"Moved {file_path} to {target_path}")
                        
        # Ensure all required directories exist
        for dir_path in cls.REQUIRED_DIRS:
            full_path = base / dir_path
            if not full_path.exists():
                actions["creates"].append(str(dir_path))
                if not dry_run:
                    full_path.mkdir(parents=True, exist_ok=True)
                    logger.debug(f"Created directory: {full_path}")
                    
        return actions
        
    @classmethod
    def clean_workspace(cls, base_path: str, remove_empty: bool = False) -> Dict[str, int]:
        """
        Clean up the workspace.
        
        Args:
            base_path: Base path of the AutoTrainX project
            remove_empty: Whether to remove empty directories
            
        Returns:
            Dictionary with cleanup statistics
        """
        base = Path(base_path)
        stats = {
            "temp_files_removed": 0,
            "empty_dirs_removed": 0,
            "cache_cleared": 0
        }
        
        # Clean temp directory
        temp_dir = base / "workspace/temp"
        if temp_dir.exists():
            for item in temp_dir.iterdir():
                if item.name != '.gitkeep':
                    if item.is_file():
                        item.unlink()
                        stats["temp_files_removed"] += 1
                    elif item.is_dir():
                        import shutil
                        shutil.rmtree(item)
                        stats["temp_files_removed"] += 1
                        
        # Clear cache if exists
        cache_dir = base / "workspace/cache"
        if cache_dir.exists():
            for item in cache_dir.iterdir():
                if item.name != '.gitkeep':
                    if item.is_file():
                        item.unlink()
                        stats["cache_cleared"] += 1
                        
        # Remove empty directories if requested
        if remove_empty:
            for dir_path in ["workspace/input", "workspace/output", "workspace/Presets", "workspace/variations"]:
                full_path = base / dir_path
                if full_path.exists():
                    for subdir in full_path.iterdir():
                        if subdir.is_dir() and not any(subdir.iterdir()):
                            subdir.rmdir()
                            stats["empty_dirs_removed"] += 1
                            
        return stats


def main():
    """CLI for workspace management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AutoTrainX Workspace Setup")
    parser.add_argument("--base-path", default=".", help="Base path of AutoTrainX project")
    parser.add_argument("--validate", action="store_true", help="Validate workspace structure")
    parser.add_argument("--setup", action="store_true", help="Set up workspace structure")
    parser.add_argument("--info", action="store_true", help="Show workspace information")
    parser.add_argument("--reorganize", action="store_true", help="Reorganize workspace")
    parser.add_argument("--clean", action="store_true", help="Clean workspace")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without doing it")
    
    args = parser.parse_args()
    
    if args.validate:
        results = WorkspaceSetup.validate_workspace(args.base_path)
        print(f"Workspace valid: {results['valid']}")
        if results['missing_required']:
            print(f"Missing required: {results['missing_required']}")
        if results['missing_optional']:
            print(f"Missing optional: {results['missing_optional']}")
            
    elif args.setup:
        success = WorkspaceSetup.setup_workspace(args.base_path, create_optional=True)
        print(f"Setup {'successful' if success else 'failed'}")
        
    elif args.info:
        info = WorkspaceSetup.get_workspace_info(args.base_path)
        print(f"Base path: {info['base_path']}")
        print("\nStatistics:")
        for key, value in info['statistics'].items():
            print(f"  {key}: {value}")
            
    elif args.reorganize:
        actions = WorkspaceSetup.reorganize_workspace(args.base_path, dry_run=args.dry_run)
        if actions['moves']:
            print("Files to move:")
            for move in actions['moves']:
                print(f"  {move}")
        if actions['creates']:
            print("Directories to create:")
            for create in actions['creates']:
                print(f"  {create}")
                
    elif args.clean:
        stats = WorkspaceSetup.clean_workspace(args.base_path, remove_empty=True)
        print(f"Cleanup statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
            
    else:
        parser.print_help()


if __name__ == "__main__":
    main()