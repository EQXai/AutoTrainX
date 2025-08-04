"""
Training routes - Web interface to CLI commands.

These routes translate web requests into CLI commands and execute them.
No internal processing is done - everything is delegated to the CLI.
"""

import logging
from fastapi import APIRouter, HTTPException, status

from ..models.simple_schemas import (
    SingleTrainingRequest,
    BatchTrainingRequest,
    VariationsTrainingRequest,
    TrainingResponse
)
from ..services.cli_translator import CLITranslator

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize CLI translator
cli_translator = CLITranslator()


@router.post(
    "/single",
    response_model=TrainingResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Execute single mode training via CLI",
    description="""
    Executes single mode training by translating the request to a CLI command.
    
    Equivalent to running:
    ```
    python main.py --train --single --source /path/to/dataset --preset SX1 --preview 3
    ```
    """
)
async def single_training(request: SingleTrainingRequest) -> TrainingResponse:
    """Execute single mode training."""
    try:
        logger.info(f"Single training request: source={request.source_path}, preset={request.preset}")
        
        result = await cli_translator.execute_single_training(
            source_path=request.source_path,
            preset=request.preset,
            dataset_name=request.dataset_name,
            repeats=request.repeats,
            class_name=request.class_name,
            preview_count=request.preview_count,
            generate_configs=request.generate_configs,
            auto_clean=request.auto_clean
        )
        
        return TrainingResponse(**result)
        
    except Exception as e:
        logger.error(f"Failed to execute single training: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute training command: {str(e)}"
        )


@router.post(
    "/batch",
    response_model=TrainingResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Execute batch mode training via CLI",
    description="""
    Executes batch mode training for multiple datasets.
    
    Equivalent to running:
    ```
    python main.py --train --batch --source /home/eqx/datasets/full --preset SX1 --parallel
    ```
    """
)
async def batch_training(request: BatchTrainingRequest) -> TrainingResponse:
    """Execute batch mode training."""
    try:
        logger.info(f"Batch training request: {len(request.datasets)} datasets, strategy={request.strategy}")
        
        # Convert dataset configs to dict format
        datasets = [ds.dict() for ds in request.datasets]
        
        result = await cli_translator.execute_batch_training(
            datasets=datasets,
            strategy=request.strategy,
            auto_clean=request.auto_clean
        )
        
        return TrainingResponse(**result)
        
    except Exception as e:
        logger.error(f"Failed to execute batch training: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute training command: {str(e)}"
        )


@router.post(
    "/variations",
    response_model=TrainingResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Execute variations mode training via CLI",
    description="""
    Executes training with parameter variations.
    
    Equivalent to running:
    ```
    python main.py --train --mode variations --source /path/to/dataset --preset FluxLORA --variations network_dim=32,64 network_alpha=16,32
    ```
    """
)
async def variations_training(request: VariationsTrainingRequest) -> TrainingResponse:
    """Execute variations mode training."""
    try:
        logger.info(f"Variations training request: source={request.source_path}, preset={request.preset}")
        
        result = await cli_translator.execute_variations_training(
            source_path=request.source_path,
            preset=request.preset,
            variations=request.variations,
            dataset_name=request.dataset_name,
            preview_count=request.preview_count,
            auto_clean=request.auto_clean
        )
        
        return TrainingResponse(**result)
        
    except Exception as e:
        logger.error(f"Failed to execute variations training: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute training command: {str(e)}"
        )


@router.get(
    "/health",
    summary="Check if training service is available",
    description="Verifies that the CLI translator can execute commands."
)
async def health_check():
    """Check training service health."""
    try:
        # Check if main.py exists
        if not cli_translator.main_script.exists():
            return {
                "status": "unhealthy",
                "message": "main.py not found"
            }
        
        return {
            "status": "healthy",
            "message": "Training service is ready",
            "cli_path": str(cli_translator.main_script)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }