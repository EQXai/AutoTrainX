"""Shared utilities for pipeline modes to avoid code duplication."""

import os
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path


class ColoredOutput:
    """ANSI color codes for terminal output."""
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    RESET = '\033[0m'
    DIM = '\033[90m'


def print_table_header(title: str, emoji: str = "", width: int = 70) -> None:
    """Print a formatted table header.
    
    Args:
        title: Title text
        emoji: Optional emoji to include
        width: Total width of the header line
    """
    if emoji:
        title_text = f" {emoji}  {title} "
    else:
        title_text = f" {title} "
    
    # Calculate padding for centering
    padding = (width - len(title_text)) // 2
    padding_left = padding
    padding_right = width - len(title_text) - padding_left
    
    print(f"\n  {ColoredOutput.CYAN}{'━' * padding_left}{title_text}{'━' * padding_right}{ColoredOutput.RESET}\n")


def print_box_single_line(content: str, width: int = 69) -> None:
    """Print content in a single-line box.
    
    Args:
        content: Content to display
        width: Width of the box (excluding borders)
    """
    print(f"  ┌{'─' * width}┐")
    print(f"  │ {content:<{width-2}} │")
    print(f"  └{'─' * width}┘")


def print_existing_datasets_warning(existing_datasets: List[str], 
                                  input_path: Path,
                                  output_path: Path,
                                  mode: str = "single") -> None:
    """Print colored warning about existing datasets.
    
    Args:
        existing_datasets: List of existing dataset names
        input_path: Path to input directory
        output_path: Path to output directory
        mode: Mode of operation ("single" or "batch")
    """
    dataset_name = existing_datasets[0] if existing_datasets else "dataset"
    
    print_table_header("EXISTING DATASET", "⚠️")
    
    # Compact warning message
    print(f"\n  Dataset '{ColoredOutput.BOLD}{dataset_name}{ColoredOutput.RESET}' already exists. This will remove:")
    print(f"  • Input:  {str(input_path / dataset_name)}")
    print(f"  • Output: {str(output_path / dataset_name)}")
    print(f"  • All preset configurations")


def get_clean_confirmation(mode: str = "single") -> str:
    """Get user confirmation for cleaning existing datasets.
    
    Args:
        mode: Mode of operation ("single" or "batch")
        
    Returns:
        User response string
    """
    prompt = f"\n  {ColoredOutput.BOLD}Clean existing dataset? (y/N):{ColoredOutput.RESET} "
    return input(prompt).strip().lower()


def print_cleaning_message(dataset_name: Optional[str] = None, mode: str = "single") -> None:
    """Print cleaning in progress message.
    
    Args:
        dataset_name: Name of dataset being cleaned (for single mode)
        mode: Mode of operation ("single" or "batch")
    """
    print_table_header("CLEANING DATASET", "🧹")
    

def print_cleaning_complete() -> None:
    """Print cleaning completion separator."""
    # Handled by the cleaning table display


def print_operation_cancelled(auto_clean_msg: bool = True) -> None:
    """Print operation cancelled message.
    
    Args:
        auto_clean_msg: Whether to show the auto-clean suggestion
    """
    print("\n")
    if auto_clean_msg:
        print_box_single_line(f"{ColoredOutput.RED}❌ Operation cancelled.{ColoredOutput.RESET} Use --auto-clean to automatically clean existing datasets.")
    else:
        print_box_single_line(f"{ColoredOutput.RED}❌ Operation cancelled.{ColoredOutput.RESET}")


def print_detailed_error(error: Exception, dataset_name: str, source_path: str, verbose: bool = True) -> None:
    """Print detailed error information.
    
    Args:
        error: The exception that occurred
        dataset_name: Name of the dataset
        source_path: Source path of the dataset
        verbose: Whether to print detailed information
    """
    if not verbose:
        return
    
    print_table_header("ERROR DETECTED", "❌")
    
    print(f"  ┌{'─' * 69}┐")
    print(f"  │ {ColoredOutput.RED}Dataset preparation failed{ColoredOutput.RESET}{'':>42} │")
    print(f"  ├{'─' * 69}┤")
    print(f"  │ Dataset:     {dataset_name:<53} │")
    print(f"  │ Source:      {str(source_path)[:53]:<53} │")
    print(f"  │ Error Type:  {type(error).__name__:<53} │")
    print(f"  │ Message:     {str(error)[:53]:<53} │")
    print(f"  └{'─' * 69}┘")
    
    # If it's a file/path related error, show more details
    if isinstance(error, (FileNotFoundError, PermissionError, OSError)):
        import traceback
        print(f"\n  {ColoredOutput.DIM}Full traceback available with --verbose flag{ColoredOutput.RESET}")


def print_dataset_extraction(dataset_name: str, source_path: str) -> None:
    """Print dataset extraction info in table format.
    
    Args:
        dataset_name: Extracted dataset name
        source_path: Source path
    """
    print_table_header("DATASET EXTRACTION")
    
    print(f"  ┌{' ' * 69}┐")
    print(f"  │ 📁 Extracted dataset name: {dataset_name:<40} │")
    print(f"  │ Source path: {str(source_path)[:54]:<54} │")
    print(f"  └{' ' * 69}┘")


def print_cleaning_table(cleaned_items: Dict[str, List[str]]) -> None:
    """Print cleaning results in table format.
    
    Args:
        cleaned_items: Dictionary with cleaned items by category
    """
    print(f"  ┌{'─' * 20}┬{'─' * 48}┐")
    print(f"  │ {'Component':<18} │ {'Path':<46} │")
    print(f"  ├{'─' * 20}┼{'─' * 48}┤")
    
    for category, paths in cleaned_items.items():
        for path in paths:
            component_name = {
                'input': '✓ Input Directory',
                'output': '✓ Output Directory',
                'presets': '✓ Preset Config'
            }.get(category, category)
            
            # Truncate path if too long
            display_path = path
            if len(path) > 46:
                display_path = '...' + path[-43:]
            
            print(f"  │ {component_name:<18} │ {display_path:<46} │")
    
    print(f"  └{'─' * 20}┴{'─' * 48}┘")


def print_dataset_prep_header(dataset_name: str, source_path: str, repeats: int, class_name: str) -> None:
    """Print dataset preparation header.
    
    Args:
        dataset_name: Name of dataset
        source_path: Source path
        repeats: Number of repeats
        class_name: Class name
    """
    print_table_header("DATASET PREPARATION")
    
    print(f"  ┌{'─' * 69}┐")
    print(f"  │ Dataset: {dataset_name:<58} │")
    print(f"  │ Source:  {str(source_path)[:58]:<58} │")
    print(f"  │ Config:  {repeats} repeats, class '{class_name}'{'':>{47-len(str(repeats))-len(class_name)}} │")
    print(f"  └{'─' * 69}┘")


def print_dataset_prep_progress(steps: List[Dict[str, Any]]) -> None:
    """Print dataset preparation progress in table format.
    
    Args:
        steps: List of step dictionaries with 'number', 'task', 'status', and 'details'
    """
    print(f"\n  ┌─────┬{'─' * 48}┬{'─' * 14}┐")
    print(f"  │ Step│ {'Task':<46} │ {'Status':<12} │")
    print(f"  ├─────┼{'─' * 48}┼{'─' * 14}┤")
    
    for step in steps:
        step_num = step.get('number', '')
        task = step.get('task', '')
        status = step.get('status', '')
        details = step.get('details', [])
        
        # Main step line
        print(f"  │  {step_num}  │ {task:<46} │ {status:<12} │")
        
        # Detail lines
        for detail in details:
            print(f"  │     │ └─ {detail:<43} │ {'':>12} │")
        
        # Add separator between steps (except last)
        if step != steps[-1]:
            print(f"  ├─────┼{'─' * 48}┼{'─' * 14}┤")
    
    print(f"  └─────┴{'─' * 48}┴{'─' * 14}┘")
    print(f"\n  {ColoredOutput.GREEN}✅ Dataset preparation completed successfully!{ColoredOutput.RESET}")


def print_summary_table(summary_data: Dict[str, str]) -> None:
    """Print summary in table format.
    
    Args:
        summary_data: Dictionary with property names and values
    """
    print_table_header("SUMMARY")
    
    # Calculate max key length for proper formatting
    max_key_len = max(len(k) for k in summary_data.keys()) if summary_data else 15
    max_key_len = min(max_key_len, 20)  # Cap at 20 chars
    
    print(f"  ┌{'─' * (max_key_len + 2)}┬{'─' * (66 - max_key_len)}┐")
    print(f"  │ {'Property':<{max_key_len}} │ {'Value':<{64 - max_key_len}} │")
    print(f"  ├{'─' * (max_key_len + 2)}┼{'─' * (66 - max_key_len)}┤")
    
    for prop, value in summary_data.items():
        # Truncate value if too long
        display_value = value
        if len(value) > (64 - max_key_len):
            display_value = value[:61 - max_key_len] + '...'
        
        print(f"  │ {prop:<{max_key_len}} │ {display_value:<{64 - max_key_len}} │")
    
    print(f"  └{'─' * (max_key_len + 2)}┴{'─' * (66 - max_key_len)}┘")


def print_file_validation_report(valid_pairs: List[Tuple[str, bool]], warnings: List[str], errors: List[str]) -> None:
    """Print file validation report in table format.
    
    Args:
        valid_pairs: List of (filename, has_caption) tuples
        warnings: List of warning messages
        errors: List of error messages
    """
    print_table_header("FILE VALIDATION REPORT")
    
    if valid_pairs:
        print(f"  ┌{'─' * 20}┬{'─' * 12}┬{'─' * 15}┬{'─' * 20}┐")
        print(f"  │ {'File Name':<18} │ {'Type':<10} │ {'Has Caption':<13} │ {'Status':<18} │")
        print(f"  ├{'─' * 20}┼{'─' * 12}┼{'─' * 15}┼{'─' * 20}┤")
        
        for filename, has_caption in valid_pairs:
            # Get file extension
            ext = Path(filename).suffix.upper()[1:] if Path(filename).suffix else 'Unknown'
            
            # Determine status
            if has_caption:
                status = f"{ColoredOutput.GREEN}✓ Valid{ColoredOutput.RESET}"
            else:
                status = f"{ColoredOutput.YELLOW}⚠️ Missing text{ColoredOutput.RESET}"
            
            # Truncate filename if needed
            display_name = filename
            if len(filename) > 18:
                display_name = filename[:15] + '...'
            
            caption_status = 'Yes' if has_caption else 'No'
            print(f"  │ {display_name:<18} │ {ext:<10} │ {caption_status:<13} │ {status:<18} │")
        
        print(f"  └{'─' * 20}┴{'─' * 12}┴{'─' * 15}┴{'─' * 20}┘")
    
    # Print warnings and errors if any
    if warnings or errors:
        print(f"\n  ┌{'─' * 69}┐")
        print(f"  │ {'Warnings:' if warnings else 'Errors:':<67} │")
        
        for warning in warnings:
            print(f"  │   • {warning[:62]:<62} │")
        
        for error in errors:
            print(f"  │   • {ColoredOutput.RED}{error[:62]:<62}{ColoredOutput.RESET} │")
        
        print(f"  └{'─' * 69}┘")
    
    # Summary
    valid_count = sum(1 for _, has_caption in valid_pairs if has_caption)
    warning_count = len([p for p in valid_pairs if not p[1]])
    error_count = len(errors)
    
    print(f"\n  Summary: {valid_count} valid pairs, {warning_count} warnings, {error_count} errors")


def print_config_generation_table(configs: List[Dict[str, str]]) -> None:
    """Print configuration generation results in table format.
    
    Args:
        configs: List of config dictionaries with 'preset', 'file', and 'status'
    """
    print_table_header("CONFIGURATION GENERATION")
    
    print(f"  ┌{'─' * 19}┬{'─' * 32}┬{'─' * 16}┐")
    print(f"  │ {'Preset':<17} │ {'Configuration File':<30} │ {'Status':<14} │")
    print(f"  ├{'─' * 19}┼{'─' * 32}┼{'─' * 16}┤")
    
    for config in configs:
        preset = config.get('preset', '')
        file = config.get('file', '')
        status = config.get('status', '✓ Generated')
        
        # Truncate if needed
        if len(preset) > 17:
            preset = preset[:14] + '...'
        if len(file) > 30:
            file = '...' + file[-27:]
        
        print(f"  │ {preset:<17} │ {file:<30} │ {ColoredOutput.GREEN}{status:<14}{ColoredOutput.RESET} │")
    
    print(f"  └{'─' * 19}┴{'─' * 32}┴{'─' * 16}┘")
    print(f"\n  Total: {len(configs)} configurations generated")


def should_show_cleaning_prompt(config: Any, is_terminal: bool = None) -> bool:
    """Determine if cleaning prompt should be shown.
    
    Args:
        config: Pipeline configuration object
        is_terminal: Whether running in terminal (None for auto-detect)
        
    Returns:
        True if prompt should be shown
    """
    if is_terminal is None:
        is_terminal = os.isatty(0)
    
    return config.verbose and is_terminal and not config.auto_clean


def format_progress_indicator(current: int, total: int, name: str, status: str = "Processing") -> str:
    """Format a progress indicator string.
    
    Args:
        current: Current item number
        total: Total number of items
        name: Name of current item
        status: Status text
        
    Returns:
        Formatted progress string
    """
    return f"\n[{current}/{total}] {status} {name}... "


def format_success_indicator(config_count: int) -> str:
    """Format a success indicator with config count.
    
    Args:
        config_count: Number of configurations generated
        
    Returns:
        Formatted success string
    """
    return f"✅ ({config_count} configs)"


def format_error_indicator() -> str:
    """Format an error indicator.
    
    Returns:
        Formatted error string
    """
    return "❌"


def format_batch_progress_header(current: int, total: int, name: str) -> str:
    """Format a cleaner batch progress header.
    
    Args:
        current: Current item number
        total: Total number of items
        name: Name of current item
        
    Returns:
        Formatted progress header string
    """
    # Use box drawing characters for a cleaner look
    progress = f"[{current}/{total}]"
    return f"\n{ColoredOutput.CYAN}━━━ {progress} {ColoredOutput.BOLD}{name}{ColoredOutput.RESET} {ColoredOutput.CYAN}{'━' * (60 - len(progress) - len(name))}{ColoredOutput.RESET}"


def format_batch_status_line(message: str, is_success: bool = True) -> str:
    """Format a status line for batch processing.
    
    Args:
        message: Status message
        is_success: Whether this is a success message
        
    Returns:
        Formatted status line
    """
    icon = f"{ColoredOutput.GREEN}✓{ColoredOutput.RESET}" if is_success else f"{ColoredOutput.RED}✗{ColoredOutput.RESET}"
    return f"    {icon} {message}"


def format_batch_summary_line(configs: int, cleaned: bool = False) -> str:
    """Format a summary line for batch processing.
    
    Args:
        configs: Number of configs generated
        cleaned: Whether dataset was cleaned
        
    Returns:
        Formatted summary line
    """
    status_parts = []
    if cleaned:
        status_parts.append(f"{ColoredOutput.YELLOW}cleaned{ColoredOutput.RESET}")
    if configs > 0:
        status_parts.append(f"{ColoredOutput.GREEN}{configs} config{'s' if configs != 1 else ''}{ColoredOutput.RESET}")
    
    status = ", ".join(status_parts) if status_parts else f"{ColoredOutput.GREEN}ready{ColoredOutput.RESET}"
    return f"    {ColoredOutput.BLUE}→{ColoredOutput.RESET} Status: {status}"


def format_training_dashboard(dataset_name: str, preset_name: str, 
                            training_script: str, config_file: str, 
                            job_id: str, command: List[str],
                            mode: str = "single", current: int = 1, total: int = 1,
                            experiment_name: Optional[str] = None,
                            variation_params: Optional[str] = None) -> str:
    """Format training information in a consistent style with training summary.
    
    Args:
        dataset_name: Name of the dataset
        preset_name: Name of the preset
        training_script: Training script name
        config_file: Path to config file
        job_id: Job ID
        command: Full command as list of strings
        mode: Execution mode ("single", "batch", "variations")
        current: Current dataset/variation number
        total: Total number of datasets/variations
        experiment_name: Name of the experiment (for variations mode)
        variation_params: Current variation parameters (for variations mode)
        
    Returns:
        Formatted dashboard string
    """
    import os
    
    lines = []
    lines.append("\n" + "=" * 80)
    lines.append(f"{'TRAINING EXECUTION':^80}")
    lines.append("=" * 80)
    
    # Basic info
    lines.append(f"Dataset:          {dataset_name}")
    lines.append(f"Preset:           {preset_name}")
    lines.append(f"Job ID:           {job_id}")
    
    # Mode info
    if mode == "single":
        lines.append(f"Mode:             Single Dataset")
    elif mode == "batch":
        lines.append(f"Mode:             Batch [{current}/{total}]")
    elif mode == "variations":
        lines.append(f"Mode:             Variations [{current}/{total}]")
        if experiment_name:
            lines.append(f"Experiment:       {experiment_name}")
        if variation_params:
            lines.append(f"Variation:        {variation_params}")
    
    lines.append(f"Training Script:  {training_script}")
    lines.append(f"Config File:      {os.path.basename(config_file)}")
    lines.append("=" * 80)
    
    return '\n'.join(lines)


def format_training_summary_dashboard(dataset_name: str, preset_name: str,
                                    duration: str, model_path: str,
                                    log_path: str, job_id: Optional[str] = None) -> str:
    """Format training summary in a technical dashboard style.
    
    Args:
        dataset_name: Name of the dataset
        preset_name: Name of the preset
        duration: Training duration
        model_path: Path to generated model
        log_path: Path to training log
        job_id: Job ID
        
    Returns:
        Formatted summary dashboard string
    """
    import os
    
    # Shorten paths if needed
    if len(model_path) > 50:
        model_parts = model_path.split('/')
        if len(model_parts) > 3:
            model_path = f".../{'/'.join(model_parts[-2:])}"
    
    if len(log_path) > 50:
        log_parts = log_path.split('/')
        if len(log_parts) > 3:
            log_path = f".../{'/'.join(log_parts[-2:])}"
    
    # Use same width as training dashboard
    width = 100
    
    lines = []
    lines.append(f"\n{ColoredOutput.GREEN}╭{'─' * width}╮{ColoredOutput.RESET}")
    lines.append(f"{ColoredOutput.GREEN}│{ColoredOutput.RESET} {ColoredOutput.BOLD}✓ TRAINING COMPLETED{ColoredOutput.RESET}                                                                          {ColoredOutput.GREEN}│{ColoredOutput.RESET}")
    lines.append(f"{ColoredOutput.GREEN}├{'─' * width}┤{ColoredOutput.RESET}")
    lines.append(f"{ColoredOutput.GREEN}│{ColoredOutput.RESET} Dataset........: {ColoredOutput.CYAN}{dataset_name:<81}{ColoredOutput.RESET} {ColoredOutput.GREEN}│{ColoredOutput.RESET}")
    lines.append(f"{ColoredOutput.GREEN}│{ColoredOutput.RESET} Preset.........: {ColoredOutput.CYAN}{preset_name:<81}{ColoredOutput.RESET} {ColoredOutput.GREEN}│{ColoredOutput.RESET}")
    lines.append(f"{ColoredOutput.GREEN}│{ColoredOutput.RESET} Duration.......: {ColoredOutput.YELLOW}{duration:<81}{ColoredOutput.RESET} {ColoredOutput.GREEN}│{ColoredOutput.RESET}")
    if job_id and job_id != "N/A":
        lines.append(f"{ColoredOutput.GREEN}│{ColoredOutput.RESET} Job ID.........: {ColoredOutput.YELLOW}{job_id:<81}{ColoredOutput.RESET} {ColoredOutput.GREEN}│{ColoredOutput.RESET}")
    lines.append(f"{ColoredOutput.GREEN}├{'─' * width}┤{ColoredOutput.RESET}")
    lines.append(f"{ColoredOutput.GREEN}│{ColoredOutput.RESET} {ColoredOutput.BOLD}Output Files:{ColoredOutput.RESET}                                                                              {ColoredOutput.GREEN}│{ColoredOutput.RESET}")
    
    if model_path != "Model not found":
        lines.append(f"{ColoredOutput.GREEN}│{ColoredOutput.RESET}   Model: {model_path:<89} {ColoredOutput.GREEN}│{ColoredOutput.RESET}")
    else:
        lines.append(f"{ColoredOutput.GREEN}│{ColoredOutput.RESET}   Model: {ColoredOutput.RED}{model_path:<89}{ColoredOutput.RESET} {ColoredOutput.GREEN}│{ColoredOutput.RESET}")
    
    lines.append(f"{ColoredOutput.GREEN}│{ColoredOutput.RESET}   Logs : {log_path:<89} {ColoredOutput.GREEN}│{ColoredOutput.RESET}")
    lines.append(f"{ColoredOutput.GREEN}╰{'─' * width}╯{ColoredOutput.RESET}")
    
    return '\n'.join(lines)


def format_batch_table_header() -> str:
    """Format the header for batch processing table.
    
    Returns:
        Formatted table header string
    """
    lines = []
    # Simplified header without the long line that can cause alignment issues
    lines.append(f"\n{ColoredOutput.CYAN}{'━' * 30} BATCH PROCESSING {'━' * 30}{ColoredOutput.RESET}")
    lines.append("")  # Empty line for spacing
    
    # Use simpler box drawing characters that align better
    lines.append("┌─────┬─────────────────┬─────────┬───────────┬──────────┬───────────────────────┐")
    lines.append("│  #  │ Dataset         │ Cleaned │ Prepared  │ Configs  │ Status                │")
    lines.append("├─────┼─────────────────┼─────────┼───────────┼──────────┼───────────────────────┤")
    
    return '\n'.join(lines)


def format_batch_table_row(current: int, total: int, dataset_name: str, 
                          cleaned: bool, prepared: bool, configs: int,
                          success: bool, error: Optional[str] = None) -> str:
    """Format a single row for the batch processing table.
    
    Args:
        current: Current dataset number
        total: Total number of datasets
        dataset_name: Name of the dataset
        cleaned: Whether dataset was cleaned
        prepared: Whether dataset was prepared
        configs: Number of configs generated
        success: Whether processing was successful
        error: Error message if failed
        
    Returns:
        Formatted table row string
    """
    # Format the row number with fixed width
    row_num = f"{current}/{total}"
    
    # Use simple text markers instead of emojis to avoid width issues
    cleaned_text = "Yes" if cleaned else "No"
    prepared_text = "Yes" if prepared else "No"
    
    # Format dataset name with fixed width
    if len(dataset_name) > 15:
        dataset_display = dataset_name[:12] + "..."
    else:
        dataset_display = dataset_name
    
    # Format status without emojis
    if not success and error:
        status = "Failed"
        status_color = ColoredOutput.RED
        dataset_color = ColoredOutput.RED
    else:
        status = "Ready"
        status_color = ColoredOutput.GREEN
        dataset_color = ""
    
    # Build the row with proper padding
    line = f"│ {row_num:^3} │ {dataset_color}{dataset_display:<15}{ColoredOutput.RESET} │ {cleaned_text:^7} │ {prepared_text:^9} │ {configs:^8} │ {status_color}{status:<21}{ColoredOutput.RESET} │"
    
    return line


def format_batch_table_footer() -> str:
    """Format the footer for batch processing table.
    
    Returns:
        Formatted table footer string
    """
    return "└─────┴─────────────────┴─────────┴───────────┴──────────┴───────────────────────┘"


def print_compact_preparation(dataset_name: str, source_path: str, repeats: int, 
                            class_name: str, was_cleaned: bool = False,
                            valid_pairs: int = 0, configs: List[str] = None) -> None:
    """Print compact dataset preparation output for single mode.
    
    Args:
        dataset_name: Name of dataset
        source_path: Source path
        repeats: Number of repeats
        class_name: Class name
        was_cleaned: Whether existing dataset was cleaned
        valid_pairs: Number of valid image-text pairs
        configs: List of generated config paths
    """
    print_table_header("DATASET PREPARATION")
    
    # Basic info
    print(f"\n  Dataset: {dataset_name} ({repeats} repeats, class '{class_name}')")
    print(f"  Source:  {source_path}")
    if was_cleaned:
        print(f"  Status:  {ColoredOutput.YELLOW}⚠️ Existing dataset cleaned{ColoredOutput.RESET}")
    print()
    
    # Compact progress table
    print(f"  ┌─────┬────────────────────────────────────────────────┬──────────────┐")
    print(f"  │ Step│ Task                                           │ Status       │")
    print(f"  ├─────┼────────────────────────────────────────────────┼──────────────┤")
    
    # Step 1 - properly format the text with padding
    task1_text = f"Validate & copy files ({valid_pairs} image-text {'pair' if valid_pairs == 1 else 'pairs'})"
    print(f"  │  1  │ {task1_text:<47} │ ✓ Complete   │")
    print(f"  │  2  │ {'Create output structure':<47} │ ✓ Complete   │")
    print(f"  │  3  │ {'Generate sample prompts':<47} │ ✓ Complete   │")
    
    if configs:
        for i, config_path in enumerate(configs):
            config_file = Path(config_path)
            parts = config_file.stem.split('_')
            preset_name = parts[1] if len(parts) >= 2 else "Unknown"
            if i == 0:
                task4_text = f"Generate configuration: {preset_name}"
                print(f"  │  4  │ {task4_text:<47} │ ✓ Complete   │")
            else:
                task_text = f"                        {preset_name}"
                print(f"  │     │ {task_text:<47} │ ✓ Complete   │")
    
    print(f"  └─────┴────────────────────────────────────────────────┴──────────────┘")
    
    # Final status
    if configs:
        config_file = Path(configs[0])
        print(f"\n  {ColoredOutput.GREEN}✅ Ready for training: {config_file.name}{ColoredOutput.RESET}")
    else:
        print(f"\n  {ColoredOutput.GREEN}✅ Dataset prepared successfully!{ColoredOutput.RESET}")


def format_batch_summary(total: int, successful: int, configs_generated: int, 
                        datasets_cleaned: int) -> str:
    """Format the summary line for batch processing.
    
    Args:
        total: Total number of datasets
        successful: Number of successful datasets
        configs_generated: Total configs generated
        datasets_cleaned: Number of datasets cleaned
        
    Returns:
        Formatted summary string
    """
    if successful == total:
        status_color = ColoredOutput.GREEN
        status_text = "All datasets ready"
    elif successful > 0:
        status_color = ColoredOutput.YELLOW
        status_text = f"{successful}/{total} completed"
    else:
        status_color = ColoredOutput.RED
        status_text = "All failed"
    
    summary = f"Summary: {status_color}{successful}/{total} completed{ColoredOutput.RESET}"
    summary += f" • {configs_generated} configs generated"
    if datasets_cleaned > 0:
        summary += f" • {datasets_cleaned} datasets cleaned"
    
    return summary