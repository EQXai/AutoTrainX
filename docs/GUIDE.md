# AutoTrainX Configuration Guide

This guide covers path configuration and ComfyUI integration setup for AutoTrainX.

## Table of Contents
- [Path Configuration](#path-configuration)
  - [Default vs Custom Paths](#default-vs-custom-paths)
  - [Using Custom Output Paths](#using-custom-output-paths)
  - [Path Profiles](#path-profiles)
- [ComfyUI Configuration](#comfyui-configuration)
- [Configuration Examples](#configuration-examples)

## Path Configuration

### Default vs Custom Paths

AutoTrainX supports two path modes:

1. **Default Mode**: All outputs are stored within the workspace directory
   ```
   AutoTrainX/workspace/
   ├── input/     # Dataset inputs
   ├── output/    # Training outputs
   └── Presets/   # Generated configurations
   ```

2. **Custom Mode**: Outputs are stored in a separate location
   ```
   AutoTrainX/workspace/input/     # Inputs always here
   /your/custom/path/              # All outputs go here
   ├── dataset1/
   ├── dataset2/
   └── variations/
   ```

### Using Custom Output Paths

#### Temporary Custom Path (Single Execution)
Use a custom path for just one execution without saving it:
```bash
python main.py --train --custom-path /path/to/external/storage --source dataset1
```

#### Persistent Custom Path
Save a custom path to config.json for all future executions:
```bash
# Set custom path
python main.py --custom-path /mnt/large_storage/models

# Clear custom path (return to default)
python main.py --custom-path ""
```

### Path Profiles

Path profiles allow you to save and switch between multiple path configurations.

#### List Available Profiles
```bash
python main.py --list-profiles
```

Output:
```
=== Path Profiles ===

📁 default
   Description: Standard workspace structure
   Custom path: None (uses default workspace)

📁 nas_storage (active)
   Description: Network attached storage for large models
   Custom path: /mnt/nas/ml_models
   Created: 2024-01-15T10:30:00
```

#### Create a New Profile
```bash
# Create profile with current settings
python main.py --save-profile "development"

# Create profile with specific custom path
python main.py --save-profile "production" --custom-path /data/production/models
```

#### Use a Profile
```bash
# Use a profile for training
python main.py --use-profile "production" --train --source dataset1

# Use a profile for preparation
python main.py --use-profile "development" --prepare --source /path/to/dataset
```

#### Delete a Profile
```bash
python main.py --delete-profile "old_profile"
```

Note: The "default" profile cannot be deleted.

#### Profile Storage
Profiles are stored in `settings/profiles.json`:
```json
{
  "default": {
    "name": "default",
    "description": "Standard workspace structure",
    "custom_output_path": null
  },
  "production": {
    "name": "production",
    "description": "Custom output path: /data/production/models",
    "custom_output_path": "/data/production/models",
    "created": "2024-01-20T14:30:00"
  }
}
```

## ComfyUI Configuration

### Set ComfyUI Path
```bash
# Set the path to your ComfyUI installation
python main.py --comfyui-path /path/to/ComfyUI

# Example
python main.py --comfyui-path /home/user/ComfyUI
```

### Check Current ComfyUI Path
The ComfyUI path is stored in `config.json`:
```json
{
  "COMFYPATH": "/home/user/ComfyUI",
  "custom_output_path": "/data/models",
  "active_profile": "production"
}
```

### ComfyUI Integration Features
When ComfyUI is configured:
- Automatic preview generation after training
- Real-time preview during training (if enabled)
- Custom workflow support for different model types

## Configuration Examples

### Example 1: Development Setup
```bash
# Create development profile with local storage
python main.py --save-profile "dev" --custom-path ~/dev/models

# Set ComfyUI path
python main.py --comfyui-path ~/ComfyUI

# Train using development profile
python main.py --use-profile "dev" --train --source dataset1 --preset FluxLORA
```

### Example 2: Production Setup with NAS
```bash
# Create production profile with network storage
python main.py --save-profile "prod" --custom-path /mnt/nas/production/models

# Train multiple datasets
python main.py --use-profile "prod" --train --batch --source /datasets/batch1
```

### Example 3: Temporary External Drive Usage
```bash
# Use external drive for one training session without saving profile
python main.py --custom-path /media/external/training --train --source dataset1
```

### Example 4: Switch Between Profiles
```bash
# Morning: Use fast local SSD
python main.py --use-profile "local_ssd" --train --source dataset1

# Evening: Switch to large capacity HDD
python main.py --use-profile "large_hdd" --train --source dataset2
```

## Path Structure Reference

### Default Mode Structure
```
AutoTrainX/
├── workspace/
│   ├── input/[dataset]/           # Input images
│   ├── output/[dataset]/          # Training outputs
│   │   ├── img/                   # Processed images
│   │   ├── model/                 # Trained models
│   │   ├── log/                   # Training logs
│   │   └── Preview/               # Generated previews
│   └── Presets/                   # Training configs
```

### Custom Mode Structure
```
AutoTrainX/
├── workspace/
│   └── input/[dataset]/           # Input images (always here)

/custom/path/
├── [dataset]/                     # All outputs
│   ├── img/
│   ├── model/
│   ├── log/
│   ├── Preview/
│   └── config/                    # Configs in custom mode
└── variations/                    # Experiment variations
```

## Best Practices

1. **Use profiles** for different environments (dev/prod/testing)
2. **Set custom paths** for:
   - Large model storage on separate drives
   - Network attached storage (NAS)
   - Faster SSDs for active development
   - Shared team directories

3. **Keep input data** in the default workspace for consistency
4. **Configure ComfyUI** early if you want preview generation
5. **Name profiles clearly** to indicate their purpose

## Troubleshooting

### Profile Not Found
```bash
Error: Profile 'myprofile' not found
```
Solution: Check available profiles with `--list-profiles`

### Custom Path Not Accessible
```bash
Error: Custom output path does not exist or is not accessible
```
Solution: Ensure the path exists and you have write permissions

### ComfyUI Not Found
```bash
Error: ComfyUI not found at specified path
```
Solution: Verify ComfyUI is installed at the specified location

## Advanced Configuration

### Environment Variables
```bash
# Override base path
export AUTOTRAINX_BASE_PATH=/custom/autotrainx/location

# Run with overridden base
python main.py --status
```

### Direct Config Editing
You can also edit `config.json` directly:
```json
{
  "COMFYPATH": "/path/to/ComfyUI",
  "custom_output_path": "/path/to/outputs",
  "active_profile": "production",
  "show_training_progress": true
}
```

Remember to use absolute paths in all configurations.