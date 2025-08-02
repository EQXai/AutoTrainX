"""Minimal box-style progress monitor without Rich dependency."""

import re
import sys
import shutil
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class TrainingState:
    """Current state of training process."""
    total_steps: Optional[int] = None
    current_step: int = 0
    current_epoch: int = 0
    total_epochs: Optional[int] = None
    current_loss: Optional[float] = None
    average_loss: Optional[float] = None
    learning_rate: Optional[float] = None
    time_per_step: Optional[float] = None
    start_time: datetime = None
    last_update: datetime = None
    phase: str = "initializing"  # initializing, preparing, training, saving, completed
    dataset_name: str = ""
    preset_name: str = ""


class MinimalProgressMonitor:
    """Monitor and display training progress with minimal box-style output."""
    
    def __init__(self, dataset_name: str = "", preset_name: str = "", quiet: bool = False):
        self.state = TrainingState(
            dataset_name=dataset_name,
            preset_name=preset_name,
            start_time=datetime.now()
        )
        self.quiet = quiet
        self.step_times = []
        self._regex_patterns = self._compile_patterns()
        self.term_width = shutil.get_terminal_size().columns
        self.box_width = min(110, self.term_width - 2)
        self.last_display_time = datetime.now()
        self.display_interval = 2.0  # Update display every 2 seconds
        self.last_displayed_step = -1  # Track last displayed step to avoid duplicates
        self.display_mode = "box"  # "box" or "line"
        
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for parsing sd-scripts output."""
        return {
            # Training steps progress: "steps:  20%|██        | 6/30 [00:18<01:13,  3.07s/it, avr_loss=0.565]"
            'progress': re.compile(
                r'steps:\s*(\d+)%\|[^|]+\|\s*(\d+)/(\d+).*?(\d+\.\d+)s/it(?:.*?avr_loss=([\d.]+))?'
            ),
            # Total optimization steps: "total optimization steps / 学習ステップ数: 30"
            'total_steps': re.compile(r'total optimization steps.*?(\d+)'),
            # Epochs: "num epochs / epoch数: 1"
            'total_epochs': re.compile(r'num epochs.*?(\d+)'),
            # Current epoch: "epoch is incremented. current_epoch: 0, epoch: 1"
            'current_epoch': re.compile(r'current_epoch:\s*(\d+),\s*epoch:\s*(\d+)'),
            # Learning rate from optimizer info
            'learning_rate': re.compile(r'LR\s+([\d.e-]+)'),
            # Model saving
            'saving': re.compile(r'saving checkpoint:|model saved'),
            # Training completion
            'completed': re.compile(r'Training completed|training finished', re.IGNORECASE),
            # Phase detection patterns
            'preparing': re.compile(r'prepare|loading|caching|Building', re.IGNORECASE),
            'training_start': re.compile(r'running training|学習開始'),
        }
        
    def parse_line(self, line: str) -> None:
        """Parse a line of output and update state."""
        # Check for phase transitions
        if self._regex_patterns['preparing'].search(line):
            if self.state.phase == "initializing":
                self.state.phase = "preparing"
        elif self._regex_patterns['training_start'].search(line):
            self.state.phase = "training"
        elif self._regex_patterns['saving'].search(line):
            self.state.phase = "saving"
        elif self._regex_patterns['completed'].search(line):
            self.state.phase = "completed"
            
        # Parse total steps
        match = self._regex_patterns['total_steps'].search(line)
        if match:
            self.state.total_steps = int(match.group(1))
            
        # Parse total epochs
        match = self._regex_patterns['total_epochs'].search(line)
        if match:
            self.state.total_epochs = int(match.group(1))
            
        # Parse current epoch
        match = self._regex_patterns['current_epoch'].search(line)
        if match:
            self.state.current_epoch = int(match.group(2))
            
        # Parse learning rate
        match = self._regex_patterns['learning_rate'].search(line)
        if match:
            self.state.learning_rate = float(match.group(1))
            
        # Parse progress line
        match = self._regex_patterns['progress'].search(line)
        if match:
            self.state.current_step = int(match.group(2))
            if not self.state.total_steps:
                self.state.total_steps = int(match.group(3))
            
            # Time per step
            time_per_step = float(match.group(4))
            self.step_times.append(time_per_step)
            if len(self.step_times) > 10:
                self.step_times.pop(0)
            self.state.time_per_step = sum(self.step_times) / len(self.step_times)
            
            # Loss
            if match.group(5):
                self.state.average_loss = float(match.group(5))
                
            self.state.last_update = datetime.now()
            
    def display(self, force: bool = False) -> None:
        """Display current progress if update interval has passed or forced."""
        if self.quiet:
            return
            
        now = datetime.now()
        
        # Check if we should update based on time and step progress
        time_elapsed = (now - self.last_display_time).total_seconds()
        step_changed = self.state.current_step != self.last_displayed_step
        
        # Only update if forced, enough time passed AND step changed, or phase changed
        if not force:
            if time_elapsed < self.display_interval:
                return
            if self.state.phase == "training" and not step_changed:
                return
                
        self.last_display_time = now
        self.last_displayed_step = self.state.current_step
        
        if self.display_mode == "line":
            self._display_line()
        else:
            self._display_box()
            
    def _display_line(self) -> None:
        """Display progress in a single line."""
        line = self.get_simple_progress_line()
        # Clear line and print
        sys.stdout.write('\r' + ' ' * self.term_width + '\r')
        sys.stdout.write(line)
        
        # Add newline when training is completed to prevent line overlap
        if self.state.phase == "completed":
            sys.stdout.write('\n')
        
        sys.stdout.flush()
        
    def _display_box(self) -> None:
        """Display progress in box format."""
        
        # Clear screen and move cursor to top
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()
        
        # Header
        print("┌" + "─" * (self.box_width - 2) + "┐")
        self._print_centered("Training Progress", self.box_width)
        print("├" + "─" * (self.box_width - 2) + "┤")
        
        # Basic info
        self._print_row(f"Dataset: {self.state.dataset_name}", self.box_width)
        self._print_row(f"Preset:  {self.state.preset_name}", self.box_width)
        self._print_row(f"Phase:   {self._get_phase_display()}", self.box_width)
        
        if self.state.phase == "training" and self.state.total_steps:
            print("├" + "─" * (self.box_width - 2) + "┤")
            
            # Progress bar
            percentage = self._get_percentage()
            bar_width = self.box_width - 20
            filled = int(bar_width * self.state.current_step / self.state.total_steps)
            bar = "█" * filled + "░" * (bar_width - filled)
            
            # Add spinner for active step
            spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
            spinner_idx = int(datetime.now().timestamp() * 10) % len(spinner_chars)
            spinner = spinner_chars[spinner_idx] if self.state.phase == "training" else "●"
            
            self._print_row(f"{spinner} Progress: {bar} {percentage:>5.1f}%", self.box_width)
            
            print("├" + "─" * (self.box_width - 2) + "┤")
            
            # Stats
            self._print_row(f"Steps:    {self.state.current_step}/{self.state.total_steps}", self.box_width)
            
            if self.state.total_epochs:
                self._print_row(f"Epoch:    {self.state.current_epoch}/{self.state.total_epochs}", self.box_width)
                
            elapsed = datetime.now() - self.state.start_time
            self._print_row(f"Elapsed:  {str(elapsed).split('.')[0]}", self.box_width)
            
            eta = self._calculate_eta()
            self._print_row(f"ETA:      {eta}", self.box_width)
            
            if self.state.average_loss is not None:
                self._print_row(f"Loss:     {self.state.average_loss:.4f}", self.box_width)
                
            if self.state.time_per_step:
                self._print_row(f"Speed:    {self.state.time_per_step:.2f}s/step", self.box_width)
        
        # Footer
        print("└" + "─" * (self.box_width - 2) + "┘")
        sys.stdout.flush()
        
    def _print_centered(self, text: str, width: int):
        """Print centered text in box."""
        padding = (width - len(text) - 2) // 2
        print("│" + " " * padding + text + " " * (width - padding - len(text) - 2) + "│")
        
    def _print_row(self, text: str, width: int):
        """Print left-aligned text in box."""
        # Handle ANSI escape codes and unicode properly
        visible_text = re.sub(r'\033\[[0-9;]*m', '', text)  # Remove ANSI codes for length calculation
        visible_text = re.sub(r'[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]', 'X', visible_text)  # Replace spinner chars
        padding_needed = width - len(visible_text) - 3
        print("│ " + text + " " * padding_needed + "│")
        
    def _get_phase_display(self) -> str:
        """Get phase display string."""
        return self.state.phase.title()
        
    def _get_percentage(self) -> float:
        """Calculate completion percentage."""
        if not self.state.total_steps:
            return 0.0
        return (self.state.current_step / self.state.total_steps) * 100
        
    def _calculate_eta(self) -> str:
        """Calculate estimated time remaining."""
        if not self.state.total_steps or not self.state.time_per_step:
            return "Calculating..."
            
        remaining_steps = self.state.total_steps - self.state.current_step
        if remaining_steps <= 0:
            return "Almost done..."
            
        remaining_seconds = remaining_steps * self.state.time_per_step
        eta = timedelta(seconds=int(remaining_seconds))
        return str(eta)
        
    def get_simple_progress_line(self) -> str:
        """Get a simple one-line progress string for logging."""
        if self.state.phase != "training" or not self.state.total_steps:
            phase_symbol = {
                "preparing": "⚙️",
                "training": "🟢",
                "saving": "💾",
                "completed": "✅",
                "initializing": "🔄"
            }.get(self.state.phase, "●")
            return f"{phase_symbol} [{self.state.phase.title()}] {self.state.dataset_name} | {self.state.preset_name}"
            
        percentage = self._get_percentage()
        eta = self._calculate_eta()
        
        # Progress bar for line mode
        bar_width = 20
        filled = int(bar_width * percentage / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        
        parts = [
            f"{self.state.dataset_name}",
            f"{bar} {percentage:.1f}%",
            f"{self.state.current_step}/{self.state.total_steps}"
        ]
        
        if self.state.average_loss is not None:
            parts.append(f"Loss: {self.state.average_loss:.4f}")
            
        parts.append(f"ETA: {eta}")
            
        return f"🟢 {' | '.join(parts)}"
        
    def set_display_mode(self, mode: str) -> None:
        """Set display mode to 'box' or 'line'."""
        if mode in ["box", "line"]:
            self.display_mode = mode


class TrainingProgressTracker:
    """Track training progress across multiple datasets."""
    
    def __init__(self):
        self.monitors = {}
        
    def create_monitor(self, dataset_name: str, preset_name: str) -> MinimalProgressMonitor:
        """Create a new progress monitor for a dataset."""
        monitor = MinimalProgressMonitor(dataset_name, preset_name)
        self.monitors[dataset_name] = monitor
        return monitor
        
    def get_monitor(self, dataset_name: str) -> Optional[MinimalProgressMonitor]:
        """Get monitor for a specific dataset."""
        return self.monitors.get(dataset_name)
        
    def display_summary(self) -> None:
        """Display summary of all training progress."""
        if not self.monitors:
            return
            
        print("\n" + "=" * 80)
        print(f"{'TRAINING SUMMARY':^80}")
        print("=" * 80)
        print(f"{'Dataset':<30} {'Status':<15} {'Progress':<15} {'Time':<20}")
        print("-" * 80)
        
        for dataset_name, monitor in self.monitors.items():
            status = monitor.state.phase.title()
            
            if monitor.state.total_steps and monitor.state.phase == "training":
                progress = f"{monitor._get_percentage():.1f}%"
            else:
                progress = "-"
                
            elapsed = datetime.now() - monitor.state.start_time
            time_str = str(elapsed).split('.')[0]
            
            print(f"{dataset_name:<30} {status:<15} {progress:<15} {time_str:<20}")
            
        print("=" * 80)