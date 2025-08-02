# AutoTrainX

Automated training pipeline for image generation models with support for FLUX, SDXL, and other architectures.

## Features

- 🚀 **Multiple Pipeline Modes**
  - Single dataset processing
  - Batch processing for multiple datasets
  - Configuration variations for hyperparameter experimentation

- 🎯 **Model Support**
  - FLUX (LoRA and full training)
  - SDXL (LoRA and checkpoint training)
  - Automatic model detection and configuration

- 🛠️ **Advanced Features**
  - Automatic dataset preparation and validation
  - Dynamic preset configuration generation
  - Resource management and cleanup
  - Comprehensive logging system
  - Progress monitoring

- 📊 **User-Friendly**
  - Interactive CLI with colored output
  - Clear error messages and guidance
  - Detailed execution logs
  - JSON output mode for scripting

## Installation

### From Source

```bash
git clone https://github.com/autotrainx/autotrainx.git
cd autotrainx
pip install -e .
```

### Development Installation

```bash
pip install -e ".[dev]"
```

### Full Installation (with UI and cloud support)

```bash
pip install -e ".[full]"
```

## Quick Start

### Prepare a Single Dataset

```bash
python main.py --prepare --source /path/to/dataset
```

### Batch Process Multiple Datasets

```bash
python main.py --prepare --mode batch --source /path/to/dataset_collection
```

### Create Configuration Variations

```bash
python main.py --prepare --mode variations --source dataset_name \
    --preset FluxLORA \
    --variations learning_rate=1e-4,1e-5 batch_size=1,2,4
```

### Check Status

```bash
python main.py --status
```

## Directory Structure

```
AutoTrainX/
├── src/                 # Source code
│   ├── pipeline/       # Pipeline implementations
│   ├── scripts/        # Dataset and preset management
│   ├── utils/          # Utilities (logging, resources)
│   └── cli/            # Command-line interface
├── workspace/          # Working directory
│   ├── input/          # Input datasets
│   ├── output/         # Processed datasets
│   └── Presets/        # Generated configurations
├── models/             # Model files
├── BasePresets/        # Preset templates
├── logs/               # Execution logs
└── tests/              # Test suite
```

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Base path (auto-detected if not set)
AUTOTRAINX_BASE_PATH=/path/to/autotrainx

# Debug settings
LOG_LEVEL=INFO
DEBUG=false

# Performance
MAX_WORKERS=4
```

### Command-Line Options

See [CLI_REFERENCE.md](CLI_REFERENCE.md) for complete command documentation.

## Documentation

- [CLI Reference](CLI_REFERENCE.md) - Complete command-line documentation
- [API Reference](docs/API_REFERENCE.md) - Python API documentation
- [Pipeline Guide](src/pipeline/README.md) - Pipeline architecture guide
- [Developer Guide](CLAUDE.md) - Development documentation

## Testing

Run the test suite:

```bash
# Install test dependencies
pip install -r tests/requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure:
- All tests pass
- Code follows the project style (run `black .` and `ruff .`)
- Documentation is updated

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built on top of [kohya-ss/sd-scripts](https://github.com/kohya-ss/sd-scripts)
- Inspired by the AI art community's training workflows
- Special thanks to all contributors

## Support

- 📖 [Documentation](https://autotrainx.readthedocs.io)
- 🐛 [Issue Tracker](https://github.com/autotrainx/autotrainx/issues)
- 💬 [Discussions](https://github.com/autotrainx/autotrainx/discussions)