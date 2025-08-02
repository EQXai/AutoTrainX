"""
AutoTrainX CLI package.

This package provides modular command-line interface components:
- parser: Command-line argument parsing
- handlers: Command execution handlers
- formatter: Output formatting and display
- unified_args: Unified argument system
- unified_handlers: Simplified command handlers
"""

from .parser import CLIParser
from .handlers import CommandHandlers
from .formatter import ResultFormatter
from .unified_args import UnifiedArgs, UnifiedArgumentParser, Operation, Mode
from .unified_handlers import UnifiedCommandHandler

__all__ = [
    'CLIParser', 'CommandHandlers', 'ResultFormatter',
    'UnifiedArgs', 'UnifiedArgumentParser', 'Operation', 'Mode',
    'UnifiedCommandHandler'
]