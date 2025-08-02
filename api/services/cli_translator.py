"""
CLI Translator Service - Converts web requests to CLI commands.

This service acts as a bridge between the web interface and the CLI,
translating HTTP requests into command-line arguments.
"""

import subprocess
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import asyncio
import json

logger = logging.getLogger(__name__)


class CLITranslator:
    """Translates web requests to CLI commands and executes them."""
    
    def __init__(self, base_path: str = "/home/eqx/AutoTrainX"):
        """
        Initialize CLI translator.
        
        Args:
            base_path: Base path where main.py is located
        """
        self.base_path = Path(base_path)
        self.main_script = self.base_path / "main.py"
        
        if not self.main_script.exists():
            raise FileNotFoundError(f"main.py not found at {self.main_script}")
    
    def build_single_command(self, 
                           source_path: str,
                           preset: str = "all",
                           dataset_name: Optional[str] = None,
                           repeats: int = 30,
                           class_name: str = "person",
                           preview_count: int = 0,
                           generate_configs: bool = True,
                           auto_clean: bool = True) -> List[str]:
        """
        Build command for single mode training.
        
        Args:
            source_path: Path to source dataset
            preset: Preset name or "all"
            dataset_name: Optional custom dataset name
            repeats: Number of repetitions (ignored in CLI bridge mode)
            class_name: Class name for object (ignored in CLI bridge mode)
            preview_count: Number of preview images
            generate_configs: Whether to generate configs
            auto_clean: Whether to auto-clean existing datasets
            
        Returns:
            Command as list of arguments
        """
        cmd = ["python", str(self.main_script), "--train", "--single"]
        
        # Required arguments
        cmd.extend(["--source", source_path])
        
        # Optional arguments
        if preset and preset != "all":
            cmd.extend(["--preset", preset])
        
        if dataset_name:
            cmd.extend(["--dataset-name", dataset_name])
        
        # Do NOT include --repeats and --class-name as per user request
        # These should be configured in the dataset itself
        
        if preview_count > 0:
            cmd.extend(["--preview", str(preview_count)])
            
        if not generate_configs:
            cmd.append("--no-config")
            
        if auto_clean:
            cmd.append("--auto-clean")
            
        return cmd
    
    def build_batch_command(self,
                          datasets: List[Dict[str, any]],
                          strategy: str = "sequential",
                          auto_clean: bool = True) -> List[str]:
        """
        Build command for batch mode training.
        
        Args:
            datasets: List of dataset configurations
            strategy: Execution strategy (sequential/parallel)
            auto_clean: Whether to auto-clean existing datasets
            
        Returns:
            Command as list of arguments
        """
        cmd = ["python", str(self.main_script), "--train", "--batch"]
        
        # Create datasets file
        datasets_file = self.base_path / "temp" / "batch_datasets.json"
        datasets_file.parent.mkdir(exist_ok=True)
        
        # Format datasets for CLI
        cli_datasets = []
        for ds in datasets:
            cli_ds = {
                "path": ds["source_path"],
                "preset": ds.get("preset", "all")
            }
            if "dataset_name" in ds:
                cli_ds["name"] = ds["dataset_name"]
            cli_datasets.append(cli_ds)
        
        with open(datasets_file, 'w') as f:
            json.dump(cli_datasets, f, indent=2)
            
        cmd.extend(["--datasets-file", str(datasets_file)])
        cmd.extend(["--strategy", strategy])
        
        if auto_clean:
            cmd.append("--auto-clean")
            
        return cmd
    
    def build_variations_command(self,
                               dataset_name: str,
                               base_preset: str,
                               variations: Dict[str, List[any]],
                               auto_clean: bool = True) -> List[str]:
        """
        Build command for variations mode training.
        
        Args:
            dataset_name: Dataset name
            base_preset: Base preset name
            variations: Parameter variations
            auto_clean: Whether to auto-clean
            
        Returns:
            Command as list of arguments
        """
        cmd = ["python", str(self.main_script), "--train", "--variations"]
        
        cmd.extend(["--dataset", dataset_name])
        cmd.extend(["--base-preset", base_preset])
        
        # Create variations file
        variations_file = self.base_path / "temp" / "variations.json"
        variations_file.parent.mkdir(exist_ok=True)
        
        with open(variations_file, 'w') as f:
            json.dump(variations, f, indent=2)
            
        cmd.extend(["--variations-file", str(variations_file)])
        
        if auto_clean:
            cmd.append("--auto-clean")
            
        return cmd
    
    async def execute_command(self, command: List[str]) -> Tuple[bool, str, str]:
        """
        Execute CLI command asynchronously.
        
        Args:
            command: Command as list of arguments
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            logger.info(f"Executing command: {' '.join(command)}")
            
            # Run command in subprocess
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.base_path)
            )
            
            stdout, stderr = await process.communicate()
            
            success = process.returncode == 0
            stdout_str = stdout.decode('utf-8') if stdout else ""
            stderr_str = stderr.decode('utf-8') if stderr else ""
            
            if success:
                logger.info("Command executed successfully")
            else:
                logger.error(f"Command failed with return code {process.returncode}")
                
            return success, stdout_str, stderr_str
            
        except Exception as e:
            logger.error(f"Failed to execute command: {e}")
            return False, "", str(e)
    
    async def execute_single_training(self, **kwargs) -> Dict[str, any]:
        """
        Execute single mode training.
        
        Returns:
            Execution result with status and output
        """
        cmd = self.build_single_command(**kwargs)
        success, stdout, stderr = await self.execute_command(cmd)
        
        # Extract job_id from output if available
        job_id = None
        for line in stdout.split('\n'):
            if 'Job ID:' in line or 'job_id:' in line.lower():
                # Extract job ID from line
                parts = line.split(':')
                if len(parts) > 1:
                    job_id = parts[1].strip()
                    break
        
        return {
            "success": success,
            "command": ' '.join(cmd),
            "output": stdout,
            "error": stderr if not success else None,
            "job_id": job_id
        }
    
    async def execute_batch_training(self, **kwargs) -> Dict[str, any]:
        """
        Execute batch mode training.
        
        Returns:
            Execution result with status and output
        """
        cmd = self.build_batch_command(**kwargs)
        success, stdout, stderr = await self.execute_command(cmd)
        
        return {
            "success": success,
            "command": ' '.join(cmd),
            "output": stdout,
            "error": stderr if not success else None
        }
    
    async def execute_variations_training(self, **kwargs) -> Dict[str, any]:
        """
        Execute variations mode training.
        
        Returns:
            Execution result with status and output
        """
        cmd = self.build_variations_command(**kwargs)
        success, stdout, stderr = await self.execute_command(cmd)
        
        return {
            "success": success,
            "command": ' '.join(cmd),
            "output": stdout,
            "error": stderr if not success else None
        }