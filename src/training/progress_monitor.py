"""Training progress monitor for sd-scripts output."""

import re
import sys
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
)
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.text import Text


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
    

class ProgressMonitor:
    """Monitor and display training progress from sd-scripts output."""
    
    def __init__(self, dataset_name: str = "", preset_name: str = "", quiet: bool = False):
        self.console = Console()
        self.state = TrainingState(
            dataset_name=dataset_name,
            preset_name=preset_name,
            start_time=datetime.now()
        )
        self.quiet = quiet
        self.step_times = []
        self._regex_patterns = self._compile_patterns()
        
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
            
    def get_progress_display(self) -> Panel:
        """Create a rich panel with current progress information."""
        # Create layout
        layout = Layout()
        
        # Header with dataset and preset info
        header = Table.grid(padding=1)
        header.add_column(style="bold cyan", no_wrap=True)
        header.add_column(style="white")
        
        header.add_row("Dataset:", self.state.dataset_name)
        header.add_row("Preset:", self.state.preset_name)
        header.add_row("Phase:", self._get_phase_display())
        
        # Progress information
        if self.state.phase == "training" and self.state.total_steps:
            progress = self._create_progress_bar()
            
            # Stats table
            stats = Table.grid(padding=1)
            stats.add_column(style="bold green", no_wrap=True)
            stats.add_column(style="white")
            
            # Calculate ETA
            eta = self._calculate_eta()
            elapsed = datetime.now() - self.state.start_time
            
            stats.add_row("Progress:", f"{self.state.current_step}/{self.state.total_steps} steps ({self._get_percentage():.1f}%)")
            if self.state.total_epochs:
                stats.add_row("Epoch:", f"{self.state.current_epoch}/{self.state.total_epochs}")
            stats.add_row("Time Elapsed:", str(elapsed).split('.')[0])
            stats.add_row("ETA:", eta)
            
            if self.state.average_loss is not None:
                stats.add_row("Average Loss:", f"{self.state.average_loss:.4f}")
            if self.state.time_per_step:
                stats.add_row("Speed:", f"{self.state.time_per_step:.2f}s/step")
                
            # Combine everything
            content = Table.grid(padding=1)
            content.add_row(header)
            content.add_row("")
            content.add_row(progress)
            content.add_row("")
            content.add_row(stats)
            
        else:
            # Just show header for non-training phases
            content = header
            
        return Panel(
            content,
            title="[bold blue]Training Progress[/bold blue]",
            border_style="blue",
            padding=(1, 2),
        )
        
    def _get_phase_display(self) -> str:
        """Get colored phase display."""
        phase_colors = {
            "initializing": "yellow",
            "preparing": "cyan",
            "training": "green",
            "saving": "magenta",
            "completed": "bold green"
        }
        color = phase_colors.get(self.state.phase, "white")
        return f"[{color}]{self.state.phase.title()}[/{color}]"
        
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
        
    def _create_progress_bar(self) -> Progress:
        """Create a rich progress bar."""
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            console=self.console,
            expand=True,
        )
        
        if self.state.total_steps:
            task = progress.add_task(
                "[cyan]Training",
                total=self.state.total_steps,
                completed=self.state.current_step
            )
            progress.update(task, completed=self.state.current_step)
            
        return progress
        
    def display_static_progress(self) -> None:
        """Display current progress (for non-live updates)."""
        if not self.quiet:
            self.console.print(self.get_progress_display())
            
    def get_simple_progress_line(self) -> str:
        """Get a simple one-line progress string."""
        if self.state.phase != "training" or not self.state.total_steps:
            return f"[{self.state.phase.title()}] {self.state.dataset_name}"
            
        percentage = self._get_percentage()
        eta = self._calculate_eta()
        
        parts = [
            f"{percentage:.1f}%",
            f"{self.state.current_step}/{self.state.total_steps}",
            f"ETA: {eta}"
        ]
        
        if self.state.average_loss is not None:
            parts.append(f"Loss: {self.state.average_loss:.4f}")
            
        return f"[Training] {' | '.join(parts)}"


class TrainingProgressTracker:
    """Track training progress across multiple datasets."""
    
    def __init__(self):
        self.monitors = {}
        self.console = Console()
        
    def create_monitor(self, dataset_name: str, preset_name: str) -> ProgressMonitor:
        """Create a new progress monitor for a dataset."""
        monitor = ProgressMonitor(dataset_name, preset_name)
        self.monitors[dataset_name] = monitor
        return monitor
        
    def get_monitor(self, dataset_name: str) -> Optional[ProgressMonitor]:
        """Get monitor for a specific dataset."""
        return self.monitors.get(dataset_name)
        
    def display_summary(self) -> None:
        """Display summary of all training progress."""
        if not self.monitors:
            return
            
        table = Table(title="Training Summary", show_header=True, header_style="bold magenta")
        table.add_column("Dataset", style="cyan", no_wrap=True)
        table.add_column("Status", style="dim")
        table.add_column("Progress", justify="right")
        table.add_column("Time", justify="right")
        
        for dataset_name, monitor in self.monitors.items():
            status_color = {
                "completed": "green",
                "training": "yellow",
                "preparing": "cyan",
                "initializing": "white",
                "saving": "magenta"
            }.get(monitor.state.phase, "white")
            
            status = f"[{status_color}]{monitor.state.phase.title()}[/{status_color}]"
            
            if monitor.state.total_steps and monitor.state.phase == "training":
                progress = f"{monitor._get_percentage():.1f}%"
            else:
                progress = "-"
                
            elapsed = datetime.now() - monitor.state.start_time
            time_str = str(elapsed).split('.')[0]
            
            table.add_row(dataset_name, status, progress, time_str)
            
        self.console.print(table)