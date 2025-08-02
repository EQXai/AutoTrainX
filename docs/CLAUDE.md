# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Build and Development
```bash
# Install dependencies
pip install -r requirements.txt

# Install development dependencies (includes black, ruff, mypy)
pip install -e ".[dev]"

# Install full dependencies (includes UI and cloud support)
pip install -e ".[full]"
```

### Code Quality
```bash
# Format code
black .

# Lint code
ruff .

# Type checking
mypy src/
```

### Testing
```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=html

# Run specific test module
pytest tests/unit/test_config.py
```

### Running the Application
```bash
# Main CLI entry point
python main.py [OPTIONS]

# Interactive menu
python menu.py

# Run via shell script
./run_menu.sh
```

### Common Usage Examples
```bash
# Train single dataset
python main.py --train --single --source /path/to/dataset --preset FluxLORA

# Train batch of datasets
python main.py --train --batch --source /path/to/dataset_collection --preset FluxLORA

# Train with variations
python main.py --train --mode variations --source dataset_name --preset FluxLORA \
       --variations network_dim=32,64,128 network_alpha=16,32

# Prepare dataset only
python main.py --prepare --single --source /path/to/dataset

# Show status
python main.py --status
```

## Architecture

### Core Components

1. **Pipeline System** (`src/pipeline/`)
   - Modular design with three modes: single, batch, and variations
   - Each mode implements `PipelineInterface` for consistent behavior
   - Factory pattern for pipeline creation
   - Hook system for extensibility

2. **Training Integration** (`src/training/`)
   - Wrapper around kohya-ss/sd-scripts for actual model training
   - Progress monitoring via `ProgressMonitor`
   - Subprocess isolation for stability

3. **Google Sheets Sync** (`src/sheets_sync/`)
   - Real-time synchronization with Google Sheets
   - Buffered service for performance
   - Queue-based architecture with workers
   - Rate limiting and retry logic

4. **Database Layer** (`src/database/`)
   - SQLAlchemy-based ORM
   - Enhanced manager with connection pooling
   - Transaction support and monitoring
   - Migration system

5. **CLI System** (`src/cli/`)
   - Unified argument parser
   - Command handlers with validation
   - Rich terminal output formatting

### Key Design Patterns

- **Factory Pattern**: Pipeline creation via `PipelineFactory`
- **Strategy Pattern**: Different execution strategies for pipeline modes
- **Observer Pattern**: Event-based sheets sync with listeners
- **Command Pattern**: CLI command handling
- **Repository Pattern**: Database access through managers

### Important Paths

- **Workspace**: `workspace/` - Contains input/output datasets and presets
- **Models**: `models/` - Model files (safetensors format)
- **Presets**: `Presets/Base/` and `Presets/Custom/` - Training configurations
- **Logs**: `logs/` - ComfyUI, pipeline, and workflow logs
- **Database**: `DB/executions.db` - SQLite database for execution tracking

### External Dependencies

- Built on top of kohya-ss/sd-scripts for training
- Integrates with ComfyUI for image preview generation
- Uses Google Sheets API for cloud synchronization
- Supports FLUX and SDXL model architectures