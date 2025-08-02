"""Validation utilities for pipeline inputs.

Provides comprehensive input validation with security checks including:
- Path traversal prevention
- Input sanitization
- Parameter bounds checking
- Type validation
- Security pattern detection
"""

import os
import re
import string
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


# Security constants
MAX_PATH_LENGTH = 4096
MAX_STRING_LENGTH = 1024
MAX_PARAM_NAME_LENGTH = 128
MAX_VARIATIONS = 100
MAX_BATCH_SIZE = 1000

# Dangerous patterns
PATH_TRAVERSAL_PATTERNS = [
    r'\.\.',  # Parent directory
    r'\.\.[\\/]',  # Parent directory with separator
    r'[\\/]\.\.',  # Separator followed by parent
    r'^~',  # Home directory expansion
    r'\$\{',  # Variable expansion
    r'\$\(',  # Command substitution
    r'`',  # Backtick command substitution
    r'\|',  # Pipe
    r'[<>]',  # Redirection
    r'&',  # Background execution
    r';',  # Command separator
    r'\n',  # Newline injection
    r'\r',  # Carriage return
    r'\x00',  # Null byte
    r'\\x[0-9a-fA-F]{2}',  # Hex escape
    r'\\[0-7]{1,3}',  # Octal escape
]

# Valid characters for different input types
VALID_PATH_CHARS = set(string.ascii_letters + string.digits + '-_./ ')
VALID_PARAM_CHARS = set(string.ascii_letters + string.digits + '-_.')
VALID_PRESET_CHARS = set(string.ascii_letters + string.digits + '-_')


def sanitize_path(path: str, allow_absolute: bool = True) -> Tuple[Optional[str], Optional[str]]:
    """
    Sanitize and validate a file path for security.
    
    Args:
        path: Path to sanitize
        allow_absolute: Whether to allow absolute paths
        
    Returns:
        Tuple of (sanitized_path, error_message)
    """
    if not path:
        return None, "Path cannot be empty"
        
    # Check length
    if len(path) > MAX_PATH_LENGTH:
        return None, f"Path too long (max {MAX_PATH_LENGTH} characters)"
        
    # Check for null bytes
    if '\x00' in path:
        return None, "Path contains null bytes"
        
    # Check for dangerous patterns
    for pattern in PATH_TRAVERSAL_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            logger.warning(f"Dangerous pattern detected in path: {pattern}")
            return None, f"Path contains potentially dangerous pattern: {pattern}"
            
    # Normalize path
    try:
        # Convert to Path object for normalization
        path_obj = Path(path)
        
        # Resolve to absolute path (follows symlinks)
        resolved = path_obj.resolve()
        
        # Check if path tries to escape using ..
        if '..' in path_obj.parts:
            return None, "Path contains parent directory references"
            
        # Check absolute path requirement
        if not allow_absolute and path_obj.is_absolute():
            return None, "Absolute paths not allowed"
            
        # Check for invalid characters
        path_str = str(resolved)
        invalid_chars = set(path_str) - VALID_PATH_CHARS
        if invalid_chars and not (os.name == 'nt' and ':' in invalid_chars and len(invalid_chars) == 1):
            return None, f"Path contains invalid characters: {invalid_chars}"
            
        return str(resolved), None
        
    except Exception as e:
        logger.error(f"Error sanitizing path: {e}")
        return None, f"Invalid path: {str(e)}"


def sanitize_string(value: str, max_length: int = MAX_STRING_LENGTH, 
                   valid_chars: Optional[set] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Sanitize a string input.
    
    Args:
        value: String to sanitize
        max_length: Maximum allowed length
        valid_chars: Set of valid characters (None for printable ASCII)
        
    Returns:
        Tuple of (sanitized_string, error_message)
    """
    if not isinstance(value, str):
        return None, "Value must be a string"
        
    if len(value) > max_length:
        return None, f"String too long (max {max_length} characters)"
        
    # Check for null bytes
    if '\x00' in value:
        return None, "String contains null bytes"
        
    # Use default valid chars if not specified
    if valid_chars is None:
        valid_chars = set(string.printable) - {'\n', '\r', '\t', '\x0b', '\x0c'}
        
    # Check for invalid characters
    invalid_chars = set(value) - valid_chars
    if invalid_chars:
        return None, f"String contains invalid characters: {invalid_chars}"
        
    # Strip whitespace
    sanitized = value.strip()
    
    return sanitized, None


def validate_numeric_param(name: str, value: Any, min_val: float, max_val: float, 
                         allow_float: bool = True) -> Optional[str]:
    """
    Validate a numeric parameter.
    
    Args:
        name: Parameter name
        value: Value to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        allow_float: Whether to allow float values
        
    Returns:
        Error message if invalid, None if valid
    """
    if not isinstance(value, (int, float)):
        return f"{name} must be numeric"
        
    if not allow_float and not isinstance(value, int):
        return f"{name} must be an integer"
        
    if value < min_val or value > max_val:
        return f"{name} must be between {min_val} and {max_val}"
        
    # Check for special float values
    if isinstance(value, float):
        if not (-float('inf') < value < float('inf')):
            return f"{name} must be a finite number"
        if value != value:  # NaN check
            return f"{name} cannot be NaN"
            
    return None


def validate_pipeline_inputs(mode: str, **kwargs) -> List[str]:
    """
    Validate pipeline inputs based on mode with security checks.
    
    Performs comprehensive validation including:
    - Mode validation
    - Parameter type checking
    - Security sanitization
    - Bounds checking
    
    Args:
        mode: Pipeline mode
        **kwargs: Mode-specific parameters
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Validate mode
    valid_modes = ['single', 'batch', 'variations']
    if mode not in valid_modes:
        errors.append(f"Invalid mode: {mode}. Must be one of: {', '.join(valid_modes)}")
        return errors
        
    # Mode-specific validation
    if mode == 'single':
        errors.extend(_validate_single_inputs(**kwargs))
    elif mode == 'batch':
        errors.extend(_validate_batch_inputs(**kwargs))
    elif mode == 'variations':
        errors.extend(_validate_variations_inputs(**kwargs))
        
    # Common validation for all modes
    errors.extend(_validate_common_inputs(**kwargs))
        
    return errors


def _validate_common_inputs(**kwargs) -> List[str]:
    """Validate common inputs across all modes."""
    errors = []
    
    # Validate output directory if provided
    output_dir = kwargs.get('output_dir')
    if output_dir:
        sanitized, error = sanitize_path(output_dir)
        if error:
            errors.append(f"Invalid output directory: {error}")
            
    # Validate model name if provided
    model_name = kwargs.get('model_name')
    if model_name:
        sanitized, error = sanitize_string(model_name, valid_chars=VALID_PRESET_CHARS)
        if error:
            errors.append(f"Invalid model name: {error}")
            
    # Validate preset if provided
    preset = kwargs.get('preset')
    if preset:
        sanitized, error = sanitize_string(preset, valid_chars=VALID_PRESET_CHARS)
        if error:
            errors.append(f"Invalid preset name: {error}")
            
    return errors


def _validate_single_inputs(**kwargs) -> List[str]:
    """Validate single pipeline inputs with security checks."""
    errors = []
    
    # Validate source path
    source_path = kwargs.get('source_path')
    if not source_path:
        errors.append("source_path is required for single mode")
    else:
        sanitized_path, error = sanitize_path(source_path)
        if error:
            errors.append(f"Invalid source path: {error}")
        elif not Path(sanitized_path).exists():
            errors.append(f"Source path does not exist: {sanitized_path}")
            
    # Validate repeats
    repeats = kwargs.get('repeats', 30)
    error = validate_numeric_param('repeats', repeats, 1, 1000, allow_float=False)
    if error:
        errors.append(error)
        
    # Validate caption extension if provided
    caption_ext = kwargs.get('caption_ext')
    if caption_ext:
        sanitized, error = sanitize_string(caption_ext, max_length=10, 
                                         valid_chars=set(string.ascii_letters + '.'))
        if error:
            errors.append(f"Invalid caption extension: {error}")
            
    return errors


def _validate_batch_inputs(**kwargs) -> List[str]:
    """Validate batch pipeline inputs with security checks."""
    errors = []
    
    # Validate datasets
    datasets = kwargs.get('datasets', [])
    if not datasets:
        errors.append("At least one dataset must be provided for batch mode")
    elif len(datasets) > MAX_BATCH_SIZE:
        errors.append(f"Too many datasets (max {MAX_BATCH_SIZE})")
    else:
        # Validate each dataset path
        for i, dataset in enumerate(datasets):
            if isinstance(dataset, dict):
                path = dataset.get('path')
                if path:
                    sanitized, error = sanitize_path(path)
                    if error:
                        errors.append(f"Dataset {i+1} - Invalid path: {error}")
            elif isinstance(dataset, str):
                sanitized, error = sanitize_path(dataset)
                if error:
                    errors.append(f"Dataset {i+1} - Invalid path: {error}")
                    
    # Validate strategy
    strategy = kwargs.get('strategy', 'sequential')
    valid_strategies = ['sequential', 'parallel']
    if strategy not in valid_strategies:
        errors.append(f"Invalid strategy: {strategy}. Must be one of: {', '.join(valid_strategies)}")
        
    # Validate max workers if parallel
    if strategy == 'parallel':
        max_workers = kwargs.get('max_workers', 4)
        error = validate_numeric_param('max_workers', max_workers, 1, 32, allow_float=False)
        if error:
            errors.append(error)
            
    return errors


def _validate_variations_inputs(**kwargs) -> List[str]:
    """Validate variations pipeline inputs with security checks."""
    errors = []
    
    # Validate dataset name
    dataset_name = kwargs.get('dataset_name')
    if not dataset_name:
        errors.append("dataset_name is required for variations mode")
    else:
        sanitized, error = sanitize_string(dataset_name, valid_chars=VALID_PRESET_CHARS)
        if error:
            errors.append(f"Invalid dataset name: {error}")
            
    # Validate base preset
    base_preset = kwargs.get('base_preset')
    if not base_preset:
        errors.append("base_preset is required for variations mode")
    else:
        sanitized, error = sanitize_string(base_preset, valid_chars=VALID_PRESET_CHARS)
        if error:
            errors.append(f"Invalid base preset: {error}")
            
    # Validate variations
    variations = kwargs.get('variations', {})
    if not variations:
        errors.append("At least one variation parameter must be provided")
    elif len(variations) > MAX_VARIATIONS:
        errors.append(f"Too many variations (max {MAX_VARIATIONS})")
    else:
        # Validate each variation parameter
        for param_name, values in variations.items():
            # Validate parameter name
            sanitized_name, error = sanitize_string(param_name, max_length=MAX_PARAM_NAME_LENGTH,
                                                  valid_chars=VALID_PARAM_CHARS)
            if error:
                errors.append(f"Invalid variation parameter name '{param_name}': {error}")
                continue
                
            # Validate values
            if not isinstance(values, list):
                errors.append(f"Variation values for '{param_name}' must be a list")
            elif len(values) > 100:
                errors.append(f"Too many values for '{param_name}' (max 100)")
                
    return errors


def validate_dataset_path(path: str) -> Optional[str]:
    """
    Validate a dataset path with security checks.
    
    Args:
        path: Path to validate
        
    Returns:
        Error message if invalid, None if valid
    """
    # Sanitize path first
    sanitized_path, error = sanitize_path(path)
    if error:
        return error
        
    path_obj = Path(sanitized_path)
    if not path_obj.exists():
        return f"Path does not exist: {sanitized_path}"
        
    if not path_obj.is_dir():
        return f"Path is not a directory: {sanitized_path}"
        
    # Check permissions
    if not os.access(sanitized_path, os.R_OK):
        return f"No read permission for: {sanitized_path}"
        
    # Check for common dataset structure
    has_images = False
    valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff']
    
    try:
        for ext in valid_extensions:
            # Use rglob with limit to prevent DOS
            count = 0
            for _ in path_obj.rglob(f'*{ext}'):
                has_images = True
                count += 1
                if count > 10:  # Early exit after finding some images
                    break
            if has_images:
                break
                
    except Exception as e:
        logger.error(f"Error scanning dataset directory: {e}")
        return f"Error scanning directory: {str(e)}"
        
    if not has_images:
        return f"No image files found in: {sanitized_path}"
        
    return None


def validate_config_parameters(config: Dict[str, Any], strict: bool = True) -> List[str]:
    """
    Validate configuration parameters with security checks.
    
    Args:
        config: Configuration dictionary
        strict: Whether to enforce strict validation
        
    Returns:
        List of validation errors
    """
    errors = []
    
    # Check config size to prevent DOS
    if len(config) > 1000:
        errors.append("Configuration has too many parameters (max 1000)")
        return errors
        
    # Extended numeric parameters with stricter bounds
    numeric_params = {
        'learning_rate': (1e-10, 1.0, True),
        'batch_size': (1, 128, False),
        'max_train_epochs': (1, 1000, False),
        'network_dim': (1, 2048, False),
        'network_alpha': (0.1, 2048, True),
        'save_every_n_epochs': (1, 100, False),
        'gradient_accumulation_steps': (1, 64, False),
        'warmup_steps': (0, 10000, False),
        'num_cpu_threads_per_process': (1, 64, False),
        'mixed_precision': (0, 1, False),
        'seed': (0, 2**32-1, False),
        'clip_skip': (1, 12, False),
        'max_token_length': (75, 300, False),
        'min_snr_gamma': (0.0, 20.0, True),
        'noise_offset': (0.0, 1.0, True),
        'adaptive_noise_scale': (0.0, 1.0, True),
        'resolution': (128, 2048, False)
    }
    
    for param, (min_val, max_val, allow_float) in numeric_params.items():
        if param in config:
            error = validate_numeric_param(param, config[param], min_val, max_val, allow_float)
            if error:
                errors.append(error)
                
    # String parameters with validation
    string_params = {
        'optimizer_type': [
            'AdamW', 'AdamW8bit', 'Lion', 'Lion8bit', 
            'SGDNesterov', 'SGDNesterov8bit', 'DAdaptation',
            'DAdaptAdam', 'DAdaptAdaGrad', 'DAdaptAdan',
            'DAdaptSGD', 'DAdaptAdanIP', 'DAdaptLion',
            'prodigyopt.Prodigy', 'PagedAdamW', 'PagedAdamW8bit',
            'PagedAdamW32bit', 'PagedLion8bit'
        ],
        'scheduler': [
            'linear', 'cosine', 'cosine_with_restarts', 'polynomial',
            'constant', 'constant_with_warmup', 'adafactor'
        ],
        'model_type': ['flux', 'sdxl', 'sd15', 'sd21'],
        'training_type': ['lora', 'checkpoint', 'dreambooth'],
        'precision': ['fp16', 'bf16', 'fp32']
    }
    
    for param, valid_values in string_params.items():
        if param in config:
            value = config[param]
            if not isinstance(value, str):
                errors.append(f"{param} must be a string")
            elif value not in valid_values:
                errors.append(f"Invalid {param}: {value}. Must be one of: {', '.join(valid_values)}")
                
    # Path parameters
    path_params = ['output_dir', 'logging_dir', 'pretrained_model_name_or_path',
                   'vae', 'resume_from_checkpoint']
    
    for param in path_params:
        if param in config and config[param]:
            sanitized, error = sanitize_path(str(config[param]))
            if error:
                errors.append(f"Invalid {param}: {error}")
                
    # Boolean parameters
    bool_params = ['train_text_encoder', 'cache_latents', 'enable_bucket',
                   'use_8bit_adam', 'gradient_checkpointing', 'xformers',
                   'shuffle_caption', 'color_aug', 'flip_aug']
    
    for param in bool_params:
        if param in config:
            if not isinstance(config[param], bool):
                errors.append(f"{param} must be a boolean")
                
    # List parameters
    if 'resolution' in config and isinstance(config['resolution'], list):
        if len(config['resolution']) != 2:
            errors.append("resolution must be a single value or list of [width, height]")
        else:
            for i, val in enumerate(config['resolution']):
                error = validate_numeric_param(f'resolution[{i}]', val, 128, 2048, False)
                if error:
                    errors.append(error)
                    
    # Validate parameter combinations
    if strict:
        errors.extend(_validate_config_combinations(config))
            
    return errors


def _validate_config_combinations(config: Dict[str, Any]) -> List[str]:
    """Validate parameter combinations for logical consistency."""
    errors = []
    
    # Check learning rate and optimizer combinations
    if 'optimizer_type' in config and 'learning_rate' in config:
        if config['optimizer_type'].startswith('DAdapt') and config['learning_rate'] > 1.0:
            errors.append("DAdapt optimizers typically use learning rate of 1.0")
            
    # Check batch size and gradient accumulation
    if 'batch_size' in config and 'gradient_accumulation_steps' in config:
        effective_batch = config['batch_size'] * config['gradient_accumulation_steps']
        if effective_batch > 256:
            errors.append(f"Effective batch size {effective_batch} may be too large")
            
    # Check resolution constraints
    if 'resolution' in config:
        res = config['resolution']
        if isinstance(res, int):
            if res % 64 != 0:
                errors.append("Resolution must be divisible by 64")
        elif isinstance(res, list) and len(res) == 2:
            if res[0] % 64 != 0 or res[1] % 64 != 0:
                errors.append("Resolution dimensions must be divisible by 64")
                
    return errors


def validate_batch_config(configs: List[Dict[str, Any]]) -> List[str]:
    """
    Validate a batch of configurations.
    
    Args:
        configs: List of configuration dictionaries
        
    Returns:
        List of validation errors
    """
    errors = []
    
    if not configs:
        errors.append("No configurations provided")
        return errors
        
    if len(configs) > MAX_BATCH_SIZE:
        errors.append(f"Too many configurations (max {MAX_BATCH_SIZE})")
        return errors
        
    for i, config in enumerate(configs):
        config_errors = validate_config_parameters(config, strict=True)
        if config_errors:
            errors.extend([f"Config {i+1}: {error}" for error in config_errors])
            
    return errors


def validate_file_upload(file_path: str, allowed_extensions: List[str],
                        max_size_mb: float = 100) -> Optional[str]:
    """
    Validate an uploaded file.
    
    Args:
        file_path: Path to the uploaded file
        allowed_extensions: List of allowed file extensions
        max_size_mb: Maximum file size in MB
        
    Returns:
        Error message if invalid, None if valid
    """
    # Sanitize path
    sanitized_path, error = sanitize_path(file_path)
    if error:
        return error
        
    path_obj = Path(sanitized_path)
    
    # Check existence
    if not path_obj.exists():
        return "File does not exist"
        
    # Check if it's a file
    if not path_obj.is_file():
        return "Path is not a file"
        
    # Check extension
    ext = path_obj.suffix.lower()
    if ext not in allowed_extensions:
        return f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        
    # Check size
    size_mb = path_obj.stat().st_size / (1024 * 1024)
    if size_mb > max_size_mb:
        return f"File too large ({size_mb:.1f}MB). Maximum: {max_size_mb}MB"
        
    # Check read permission
    if not os.access(sanitized_path, os.R_OK):
        return "No read permission for file"
        
    return None