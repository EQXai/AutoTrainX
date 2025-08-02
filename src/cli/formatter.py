"""
Result formatter for AutoTrainX CLI output.

This module handles all output formatting and display functionality,
providing a clean separation between data processing and presentation.
"""

from typing import Dict, Any, Optional
import json

from src.pipeline.pipeline import PipelineResult


class ResultFormatter:
    """Handles formatting and display of results and status information."""
    
    def __init__(self, json_output: bool = False):
        self.json_output = json_output
    
    def print_separator(self, title: str = "", width: int = 70):
        """Print a formatted separator with optional title."""
        if self.json_output:
            return
            
        if title:
            padding = (width - len(title) - 2) // 2
            print("=" * padding + f" {title} " + "=" * padding)
        else:
            print("=" * width)
    
    def print_result_summary(self, result: PipelineResult):
        """Print a formatted summary of pipeline results."""
        if self.json_output:
            self._print_json_result(result)
            return
        
        self.print_separator("PIPELINE RESULT SUMMARY")
        
        # Handle new modular result format
        if hasattr(result, 'mode'):
            self._print_modular_result(result)
        else:
            # Legacy format
            self._print_legacy_result(result)
        
        if result.error_message:
            print(f"\nError: {result.error_message}")
        
        self.print_separator()
    
    def _print_modular_result(self, result: PipelineResult):
        """Print results in modular format."""
        print(f"Mode: {result.mode.upper()}")
        print(f"Status: {result.status.value}")
        
        if result.mode == 'single':
            self._print_single_mode_result(result)
        elif result.mode in ['batch', 'variations']:
            self._print_batch_mode_result(result)
        
        # Check if result has configs_generated attribute before accessing it
        if hasattr(result, 'configs_generated') and result.configs_generated and hasattr(result, 'preset_configs') and result.preset_configs:
            self._print_generated_configs(result.preset_configs)
    
    def _print_single_mode_result(self, result: PipelineResult):
        """Print single mode specific results."""
        if hasattr(result, 'dataset_name'):
            print(f"Dataset: {result.dataset_name}")
        if hasattr(result, 'dataset_prepared') and result.dataset_prepared:
            print("✓ Dataset Prepared:")
            if hasattr(result, 'input_dir'):
                print(f"   Input Dir: {result.input_dir}")
            if hasattr(result, 'output_dir'):
                print(f"   Output Dir: {result.output_dir}")
            if hasattr(result, 'prompts_file'):
                print(f"   Prompts File: {result.prompts_file}")
            if hasattr(result, 'repeats') and hasattr(result, 'class_name'):
                print(f"   Configuration: {result.repeats} repeats, class '{result.class_name}'")
    
    def _print_batch_mode_result(self, result: PipelineResult):
        """Print batch/variations mode specific results."""
        if hasattr(result, 'total_datasets'):
            print(f"Total: {result.total_datasets}")
        if hasattr(result, 'successful_datasets'):
            print(f"Successful: {result.successful_datasets}")
        if hasattr(result, 'failed_datasets'):
            print(f"Failed: {result.failed_datasets}")
        if hasattr(result, 'success_rate'):
            print(f"Success Rate: {result.success_rate:.1%}")
        
        if hasattr(result, 'results') and result.results:
            print("\nResults:")
            for name, dataset_result in result.results.items():
                status = "✓" if hasattr(dataset_result, 'success') and dataset_result.success else "✗"
                print(f"   {status} {name}")
                if hasattr(dataset_result, 'error') and dataset_result.error:
                    print(f"      Error: {dataset_result.error}")
    
    def _print_legacy_result(self, result: PipelineResult):
        """Print results in legacy format."""
        print(f"Operation: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Dataset: {result.dataset_name}")
        
        if hasattr(result, 'dataset_prepared') and result.dataset_prepared:
            print("✓ Dataset Prepared:")
            print(f"   Input Dir: {result.input_dir}")
            print(f"   Output Dir: {result.output_dir}")
            print(f"   Prompts File: {result.prompts_file}")
            print(f"   Configuration: {result.repeats} repeats, class '{result.class_name}'")
        
        if hasattr(result, 'configs_generated') and result.configs_generated and hasattr(result, 'preset_configs') and result.preset_configs:
            self._print_generated_configs(result.preset_configs)
    
    def _print_generated_configs(self, preset_configs: Dict[str, list]):
        """Print generated configuration information."""
        print("\n✓ Configurations Generated:")
        for dataset, configs in preset_configs.items():
            print(f"   {dataset}: {len(configs)} configurations")
            if hasattr(configs[0], '__dict__'):  # If configs are objects
                for config in configs:
                    print(f"     - {config}.toml")
    
    def print_status(self, status: Dict[str, Any]):
        """Print pipeline status information."""
        if self.json_output:
            print(json.dumps(status, indent=2))
            return
        
        self.print_separator("AUTOTRAINX PIPELINE STATUS")
        
        print(f"Base Path: {status['base_path']}")
        print(f"Status: {status['pipeline_status']}")
        
        self._print_datasets_status(status['datasets'])
        if 'variations' in status:
            self._print_variations_status(status['variations'])
        self._print_presets_status(status['presets'])
        self._print_configs_status(status['configurations'])
        self._print_directories_status(status['directories'])
        
        self.print_separator()
    
    def _print_datasets_status(self, datasets: Dict[str, Any]):
        """Print dataset status information."""
        print("\nDATASETS:")
        print(f"   Input datasets: {datasets['total_input']}")
        if datasets['input_datasets']:
            for dataset in datasets['input_datasets']:
                print(f"     - {dataset}")
        
        print(f"   Output datasets: {datasets['total_output']}")
        if datasets['output_datasets']:
            for dataset in datasets['output_datasets']:
                print(f"     - {dataset}")
    
    def _print_variations_status(self, variations: Dict[str, Any]):
        """Print variations experiments status information."""
        print("\nVARIATION EXPERIMENTS:")
        print(f"   Total experiments: {variations['total_experiments']}")
        if variations['experiments']:
            for exp in variations['experiments']:
                print(f"   - Experiment ID: exp_{exp['variation_id']}")
                print(f"     Dataset: {exp['dataset']}")
                print(f"     Preset: {exp['preset']}")
                print(f"     Created: {exp['created']}")
                print(f"     Total variations: {exp['total_variations']}")
                print(f"     Parameters varied: {exp['parameters_varied']}")
    
    def _print_presets_status(self, presets: Dict[str, Any]):
        """Print preset status information."""
        print("\nPRESETS:")
        print(f"   Available presets: {presets['total_presets']}")
        for preset, description in presets['preset_descriptions'].items():
            print(f"     - {preset}: {description}")
    
    def _print_configs_status(self, configs: Dict[str, Any]):
        """Print configuration status information."""
        print("\nCONFIGURATIONS:")
        print(f"   Generated configs: {configs['total_configs']}")
        if configs['generated_configs']:
            for config in configs['generated_configs']:
                print(f"     - {config}.toml")
    
    def _print_directories_status(self, dirs: Dict[str, Any]):
        """Print directory status information."""
        print("\nDIRECTORIES:")
        print(f"   Input: {dirs['input_path']}")
        print(f"   Output: {dirs['output_path']}")
        print(f"   Presets: {dirs['presets_path']}")
    
    def print_presets(self, presets: Dict[str, str]):
        """Print available presets."""
        # Enhanced to show base vs custom presets
        from src.scripts.preset_manager import get_preset_manager
        preset_manager = get_preset_manager()
        
        if self.json_output:
            # Enhanced JSON output with preset types
            preset_list = []
            for name, description in presets.items():
                preset_info = preset_manager.get_preset(name)
                preset_list.append({
                    "name": name,
                    "description": description,
                    "type": preset_info.preset_type if preset_info else "unknown",
                    "is_custom": preset_info.is_custom if preset_info else False,
                    "base_preset": preset_info.base_preset if preset_info else None
                })
            print(json.dumps({"presets": preset_list}, indent=2))
            return
        
        self.print_separator("AVAILABLE PRESETS")
        
        if not presets:
            print("No presets available.")
        else:
            # Separate base and custom presets
            base_presets = preset_manager.get_base_presets()
            custom_presets = preset_manager.list_custom_presets()
            
            if base_presets:
                print("\n\033[96mBase Presets:\033[0m")
                for name in sorted(base_presets):
                    if name in presets:
                        print(f"• {name}")
                        print(f"   {presets[name]}")
                        print()
            
            if custom_presets:
                print("\n\033[93mCustom Presets:\033[0m")
                for name in sorted(custom_presets):
                    if name in presets:
                        preset_info = preset_manager.get_preset(name)
                        print(f"• {name}")
                        print(f"   {presets[name]}")
                        if preset_info and preset_info.base_preset:
                            print(f"   \033[90m(based on: {preset_info.base_preset})\033[0m")
                        print()
            
            print(f"Total: {len(presets)} presets available ({len(base_presets)} base, {len(custom_presets)} custom)")
        
        self.print_separator()
    
    def print_dataset_info(self, dataset_name: str, info: Dict[str, Any]):
        """Print detailed information about a specific dataset."""
        if self.json_output:
            print(json.dumps({"dataset": dataset_name, "info": info}, indent=2))
            return
        
        self.print_separator(f"DATASET INFO: {dataset_name}")
        
        print(f"Dataset Directory: {info['dataset_dir']}")
        print(f"Training Directory: {info['training_dir']}")
        print(f"Model Directory: {info['model_dir']}")
        print(f"Log Directory: {info['log_dir']}")
        
        print(f"\nSTATISTICS:")
        print(f"   Images: {info['total_images']}")
        print(f"   Text files: {info['total_texts']}")
        print(f"   Sample prompts: {'✓ Available' if info['has_sample_prompts'] else '✗ Missing'}")
        
        if info['has_sample_prompts']:
            print(f"   Prompts file: {info['sample_prompts_file']}")
        
        self.print_separator()
    
    def _print_json_result(self, result: PipelineResult):
        """Print result in JSON format."""
        result_dict = {
            "success": result.success,
            "mode": getattr(result, 'mode', 'unknown'),
            "status": getattr(result.status, 'value', 'unknown') if hasattr(result, 'status') else 'unknown',
        }
        
        if hasattr(result, 'dataset_name'):
            result_dict["dataset_name"] = result.dataset_name
        
        if hasattr(result, 'error_message') and result.error_message:
            result_dict["error"] = result.error_message
        
        if hasattr(result, 'results'):
            result_dict["results"] = {
                name: {
                    "success": r.success,
                    "error": r.error if hasattr(r, 'error') else None
                }
                for name, r in result.results.items()
            }
        
        print(json.dumps(result_dict, indent=2))