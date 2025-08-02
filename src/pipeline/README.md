# Pipeline Module

The pipeline module provides a modular, extensible system for dataset preparation and configuration generation in AutoTrainX.

## Architecture

```
pipeline/
├── base/               # Abstract interfaces and base classes
│   ├── pipeline_interface.py    # Core pipeline interface
│   ├── pipeline_result.py       # Result data structures
│   ├── pipeline_context.py      # Execution context management
│   └── pipeline_exceptions.py   # Custom exceptions
├── modes/              # Pipeline implementation modes
│   ├── single_pipeline.py       # Single dataset processing
│   ├── batch_pipeline.py        # Batch processing
│   └── variations_pipeline.py   # Configuration variations
├── utils/              # Utility modules
│   ├── pipeline_factory.py      # Factory pattern implementation
│   ├── shared_pipeline_utils.py # Shared utilities
│   ├── validation.py           # Input validation
│   └── monitoring.py           # Progress monitoring
├── strategies/         # Execution strategies (future)
└── pipeline.py        # Main pipeline facade
```

## Core Concepts

### Pipeline Interface
All pipeline modes implement the `PipelineInterface` abstract base class, ensuring consistent behavior:

```python
class PipelineInterface(ABC):
    @abstractmethod
    def execute(self, **kwargs) -> PipelineResult:
        """Execute the pipeline with provided parameters."""
        pass
    
    @abstractmethod
    def validate_inputs(self, **kwargs) -> List[str]:
        """Validate input parameters before execution."""
        pass
    
    @abstractmethod
    def get_execution_plan(self, **kwargs) -> Dict[str, Any]:
        """Generate execution plan without running."""
        pass
```

### Pipeline Modes

#### Single Pipeline
Processes one dataset at a time with full control:
- Dataset preparation
- Output structure creation
- Sample prompts generation
- Preset configuration generation

#### Batch Pipeline
Processes multiple datasets efficiently:
- Sequential or parallel execution
- Error handling with continue-on-error
- Progress tracking
- Aggregate results

#### Variations Pipeline
Creates configuration variations for experimentation:
- Parameter grid generation
- Multiple config file creation
- Naming template support

### Pipeline Context
Manages execution state and metadata:
- Thread-safe operation tracking
- Error collection
- Dataset processing history
- Configuration generation tracking

### Pipeline Results
Structured results with detailed information:
- Execution status
- Per-dataset results
- Error messages
- Timing information
- Generated file paths

## Usage Examples

### Single Dataset Processing
```python
from src.pipeline import AutoTrainPipeline

pipeline = AutoTrainPipeline()
result = pipeline.execute(
    mode='single',
    source_path='/path/to/dataset',
    repeats=30,
    class_name='person'
)
```

### Batch Processing
```python
result = pipeline.execute(
    mode='batch',
    datasets=[
        {'source_path': '/path/to/dataset1'},
        {'source_path': '/path/to/dataset2'}
    ],
    strategy='parallel'
)
```

### Configuration Variations
```python
result = pipeline.execute(
    mode='variations',
    dataset_name='my_dataset',
    base_preset='FluxLORA',
    variations={
        'learning_rate': [1e-4, 1e-5],
        'batch_size': [1, 2, 4]
    }
)
```

## Extending the Pipeline

### Adding a New Mode
1. Create a new class in `modes/` that inherits from `PipelineInterface`
2. Implement required methods: `execute`, `validate_inputs`, `get_execution_plan`
3. Register the mode in `pipeline.py`

### Adding Utilities
Shared utilities should be added to `utils/shared_pipeline_utils.py` to avoid code duplication.

### Future Enhancements
- Execution strategies (parallel, distributed)
- Pipeline composition
- Checkpoint/resume support
- Real-time progress streaming