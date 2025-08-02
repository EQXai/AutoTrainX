"""Batch processing pipeline for multiple datasets."""

from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import concurrent.futures
from ..base import PipelineInterface, PipelineConfig, PipelineResult, DatasetResult, PipelineStatus
from ..base.pipeline_context import PipelineContext
from .single_pipeline import SinglePipeline
from ...scripts.dataset_preparation import extract_dataset_name
from ..utils.shared_pipeline_utils import (
    print_existing_datasets_warning,
    get_clean_confirmation,
    print_cleaning_message,
    print_cleaning_complete,
    print_operation_cancelled,
    format_progress_indicator,
    format_success_indicator,
    format_error_indicator,
    format_batch_progress_header,
    format_batch_status_line,
    format_batch_summary_line,
    format_batch_table_header,
    format_batch_table_row,
    format_batch_table_footer,
    format_batch_summary
)
import uuid
from datetime import datetime


class BatchPipeline(PipelineInterface):
    """
    Pipeline for processing multiple datasets in batch.
    
    Supports both sequential and parallel execution strategies
    with comprehensive error handling and partial success support.
    """
    
    def __init__(self, config: PipelineConfig):
        super().__init__(config)
        self.single_pipeline = SinglePipeline(config)
        
    def execute(self, datasets: List[Union[str, Dict[str, Any]]],
                strategy: str = 'sequential',
                continue_on_error: bool = True,
                preset: Optional[str] = None) -> PipelineResult:
        """
        Execute batch pipeline on multiple datasets.
        
        Args:
            datasets: List of dataset paths or configurations
            strategy: Execution strategy ('sequential' or 'parallel')
            continue_on_error: Whether to continue processing on errors
            preset: Optional specific preset to generate configs for
            
        Returns:
            PipelineResult with batch execution details
        """
        context = PipelineContext(pipeline_id=str(uuid.uuid4()))
        start_time = datetime.now()
        
        # Validate inputs
        errors = self.validate_inputs(datasets=datasets)
        if errors:
            return self._create_error_result(errors, context)
            
        # Normalize dataset inputs
        normalized_datasets = self._normalize_datasets(datasets)
        
        # Execute based on strategy
        if strategy == 'parallel' and self.config.parallel:
            results = self._execute_parallel(normalized_datasets, context, continue_on_error, preset)
        else:
            results = self._execute_sequential(normalized_datasets, context, continue_on_error, preset)
            
        # Aggregate results
        total = len(normalized_datasets)
        successful = sum(1 for r in results.values() if r.success)
        failed = total - successful
        
        # Determine overall status
        if successful == total:
            status = PipelineStatus.SUCCESS
        elif successful > 0:
            status = PipelineStatus.PARTIAL_SUCCESS
        else:
            status = PipelineStatus.FAILED
            
        return PipelineResult(
            status=status,
            mode='batch',
            total_datasets=total,
            successful_datasets=successful,
            failed_datasets=failed,
            results=results,
            execution_time=(datetime.now() - start_time).total_seconds(),
            context=context
        )
        
    def validate_inputs(self, **kwargs) -> List[str]:
        """Validate batch pipeline inputs."""
        errors = []
        
        datasets = kwargs.get('datasets', [])
        if not datasets:
            errors.append("At least one dataset must be provided")
            
        for i, dataset in enumerate(datasets):
            if isinstance(dataset, str):
                if not Path(dataset).exists():
                    errors.append(f"Dataset {i}: Path does not exist: {dataset}")
            elif isinstance(dataset, dict):
                if 'source_path' not in dataset:
                    errors.append(f"Dataset {i}: Missing required 'source_path'")
            else:
                errors.append(f"Dataset {i}: Invalid type (must be string or dict)")
                
        return errors
        
    def get_execution_plan(self, **kwargs) -> Dict[str, Any]:
        """Get execution plan for batch processing."""
        datasets = kwargs.get('datasets', [])
        strategy = kwargs.get('strategy', 'sequential')
        
        normalized = self._normalize_datasets(datasets)
        
        return {
            'mode': 'batch',
            'strategy': strategy,
            'datasets': [
                {
                    'name': d['dataset_name'],
                    'source': d['source_path'],
                    'repeats': d.get('repeats', 30),
                    'class_name': d.get('class_name', 'person')
                }
                for d in normalized
            ],
            'total_datasets': len(normalized),
            'estimated_time': f"{len(normalized) * 0.5:.1f} minutes ({'parallel' if strategy == 'parallel' else 'sequential'})"
        }
        
    def _normalize_datasets(self, datasets: List[Union[str, Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Normalize dataset inputs to consistent format."""
        normalized = []
        
        for dataset in datasets:
            if isinstance(dataset, str):
                # Simple path string
                normalized.append({
                    'source_path': dataset,
                    'dataset_name': extract_dataset_name(dataset, quiet=True),
                    'repeats': 30,
                    'class_name': 'person'
                })
            else:
                # Configuration dictionary
                config = dataset.copy()
                if 'dataset_name' not in config:
                    config['dataset_name'] = extract_dataset_name(config['source_path'], quiet=True)
                config.setdefault('repeats', 30)
                config.setdefault('class_name', 'person')
                normalized.append(config)
                
        return normalized
        
    def _execute_sequential(self, datasets: List[Dict[str, Any]], 
                          context: PipelineContext,
                          continue_on_error: bool,
                          preset: Optional[str] = None) -> Dict[str, DatasetResult]:
        """Execute datasets sequentially."""
        results = {}
        total = len(datasets)
        
        # Check for existing datasets first
        existing_datasets = []
        for dataset_config in datasets:
            dataset_name = dataset_config['dataset_name']
            if self.single_pipeline.dataset_preparator.check_existing_dataset(dataset_name):
                existing_datasets.append(dataset_name)
                
        # If there are existing datasets and auto-clean is not enabled, ask user
        if existing_datasets and not self.config.auto_clean:
            print_existing_datasets_warning(
                existing_datasets,
                self.single_pipeline.dataset_preparator.input_path,
                self.single_pipeline.dataset_preparator.output_path,
                mode="batch"
            )
            
            response = get_clean_confirmation(mode="batch")
            if response in ['y', 'yes']:
                print_cleaning_message(mode="batch")
                self.config.auto_clean = True
                print_cleaning_complete()
            else:
                print_operation_cancelled(auto_clean_msg=True)
                # Mark existing datasets as failed
                for name in existing_datasets:
                    results[name] = DatasetResult(
                        dataset_name=name,
                        success=False,
                        error="Dataset already exists and user chose not to clean it"
                    )
                # Process only non-existing datasets
                datasets = [d for d in datasets if d['dataset_name'] not in existing_datasets]
                if not datasets:
                    return results
        
        # Print table header
        print(format_batch_table_header())
        
        # Track statistics for summary
        total_configs = 0
        total_cleaned = 0
        
        # Process datasets
        for idx, dataset_config in enumerate(datasets, 1):
            dataset_name = dataset_config['dataset_name']
            
            # Track if dataset was cleaned
            was_cleaned = dataset_name in existing_datasets
            
            try:
                # Process single dataset
                result = self._process_single_dataset(dataset_config, context, preset)
                results[dataset_name] = result
                
                if result.success:
                    # Count generated configs
                    config_count = len(result.configs) if result.configs else 0
                    total_configs += config_count
                    if was_cleaned:
                        total_cleaned += 1
                    
                    # Print table row
                    print(format_batch_table_row(
                        current=idx,
                        total=total,
                        dataset_name=dataset_name,
                        cleaned=was_cleaned,
                        prepared=True,
                        configs=config_count,
                        success=True
                    ))
                else:
                    # Print error row
                    print(format_batch_table_row(
                        current=idx,
                        total=total,
                        dataset_name=dataset_name,
                        cleaned=was_cleaned,
                        prepared=False,
                        configs=0,
                        success=False,
                        error=result.error
                    ))
                
                if not result.success and not continue_on_error:
                    break
                    
            except Exception as e:
                error_result = DatasetResult(
                    dataset_name=dataset_name,
                    success=False,
                    error=str(e)
                )
                results[dataset_name] = error_result
                
                # Print error row
                print(format_batch_table_row(
                    current=idx,
                    total=total,
                    dataset_name=dataset_name,
                    cleaned=was_cleaned,
                    prepared=False,
                    configs=0,
                    success=False,
                    error=str(e)
                ))
                
                if not continue_on_error:
                    break
        
        # Print table footer
        print(format_batch_table_footer())
        
        # Count successful datasets
        successful_count = sum(1 for r in results.values() if r.success)
        
        # Print summary
        print(format_batch_summary(
            total=len(results),
            successful=successful_count,
            configs_generated=total_configs,
            datasets_cleaned=total_cleaned
        ))
        print()  # Extra line for spacing
                    
        return results
        
    def _execute_parallel(self, datasets: List[Dict[str, Any]],
                         context: PipelineContext,
                         continue_on_error: bool,
                         preset: Optional[str] = None) -> Dict[str, DatasetResult]:
        """Execute datasets in parallel."""
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            future_to_dataset = {
                executor.submit(self._process_single_dataset, dataset_config, context, preset): dataset_config
                for dataset_config in datasets
            }
            
            for future in concurrent.futures.as_completed(future_to_dataset):
                dataset_config = future_to_dataset[future]
                dataset_name = dataset_config['dataset_name']
                
                try:
                    result = future.result()
                    results[dataset_name] = result
                except Exception as e:
                    error_result = DatasetResult(
                        dataset_name=dataset_name,
                        success=False,
                        error=str(e)
                    )
                    results[dataset_name] = error_result
                    
        return results
        
    def _process_single_dataset(self, dataset_config: Dict[str, Any],
                               context: PipelineContext,
                               preset: Optional[str] = None) -> DatasetResult:
        """Process a single dataset configuration."""
        # For batch mode, we need to create our own execution record
        from ...utils.job_id import generate_job_id
        from ...utils.job_tracker import get_tracker
        from ...database import ExecutionStatus, PipelineMode
        
        job_id = generate_job_id()
        tracker = get_tracker()
        dataset_name = dataset_config['dataset_name']
        preset_name = preset if preset else "all"
        
        # Create execution record with BATCH pipeline mode
        tracker.create_execution(
            job_id=job_id,
            pipeline_mode=PipelineMode.BATCH.value,
            dataset_name=dataset_name,
            preset=preset_name
        )
        
        try:
            # Track dataset preparation stage
            with tracker.track_stage(job_id, ExecutionStatus.PREPARING_DATASET):
                # Execute dataset preparation
                prep_result = self.single_pipeline._prepare_dataset(
                    dataset_config['source_path'],
                    dataset_name,
                    dataset_config.get('repeats', 30),
                    dataset_config.get('class_name', 'person'),
                    auto_clean=self.config.auto_clean
                )
            
            configs = []
            if dataset_config.get('generate_configs', True) and prep_result['success']:
                # Track configuration generation stage
                with tracker.track_stage(job_id, ExecutionStatus.CONFIGURING_PRESET):
                    # Generate configurations
                    configs = self.single_pipeline._generate_configurations(dataset_name, preset, job_id)
            
            # Create dataset result
            dataset_result = DatasetResult(
                dataset_name=dataset_name,
                success=prep_result['success'],
                input_dir=prep_result.get('input_dir'),
                output_dir=prep_result.get('output_dir'),
                prompts_file=prep_result.get('prompts_file'),
                configs=configs,
                error=prep_result.get('error')
            )
            
            # Update status based on preparation result
            if not prep_result['success']:
                tracker.update_status(job_id, ExecutionStatus.FAILED, error_message=prep_result.get('error'))
            elif dataset_config.get('generate_configs', True) and configs:
                # Configuration is complete, mark as ready for training
                tracker.update_status(job_id, ExecutionStatus.READY_FOR_TRAINING)
            else:
                # Just preparation was done
                tracker.update_status(job_id, ExecutionStatus.DONE)
            
            # Set output path if successful
            if prep_result['success'] and prep_result.get('output_dir'):
                tracker.set_output_path(job_id, str(prep_result['output_dir']))
            
            return dataset_result
            
        except Exception as e:
            # Update tracker with error
            tracker.update_status(job_id, ExecutionStatus.FAILED, error_message=str(e))
            return DatasetResult(
                dataset_name=dataset_name,
                success=False,
                error=str(e)
            )
        
    def _create_error_result(self, errors: List[str], context: PipelineContext) -> PipelineResult:
        """Create error result."""
        return PipelineResult(
            status=PipelineStatus.FAILED,
            mode='batch',
            total_datasets=0,
            successful_datasets=0,
            failed_datasets=0,
            context=context,
            error_message="; ".join(errors)
        )