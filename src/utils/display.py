"""Display utilities for AutoTrainX."""

from typing import List, Optional, Dict
import shutil
import re


class DisplayBox:
    """Utility class for creating bordered text boxes."""
    
    # Box drawing characters
    STYLES = {
        'modern': {
            'tl': '╭', 'tr': '╮', 'bl': '╰', 'br': '╯',
            'h': '─', 'v': '│', 'dot': '·'
        },
        'classic': {
            'tl': '┌', 'tr': '┐', 'bl': '└', 'br': '┘',
            'h': '─', 'v': '│', 'dot': '·'
        },
        'double': {
            'tl': '╔', 'tr': '╗', 'bl': '╚', 'br': '╝',
            'h': '═', 'v': '║', 'dot': '·'
        },
        'rounded': {
            'tl': '╭', 'tr': '╮', 'bl': '╰', 'br': '╯',
            'h': '─', 'v': '│', 'dot': '·'
        }
    }
    
    @staticmethod
    def create_box(title: str, lines: List[str], width: Optional[int] = None, 
                   padding: int = 3, style: str = 'modern', center_content: bool = False) -> str:
        """Create a bordered box with content.
        
        Args:
            title: Title for the box
            lines: Lines of content to display
            width: Box width (auto-detected if None)
            padding: Padding on each side
            style: Box style ('modern', 'classic', 'double', 'rounded')
            center_content: Whether to center content lines
            
        Returns:
            String representation of the box
        """
        # Get style characters
        chars = DisplayBox.STYLES.get(style, DisplayBox.STYLES['modern'])
        
        # Get terminal width
        terminal_width = shutil.get_terminal_size().columns
        
        # Clean lines - remove ANSI color codes for length calculation
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_lines = [ansi_escape.sub('', line) for line in lines]
        
        # Calculate box width
        if width is None:
            # Find longest line including title
            max_len = len(title) + 10  # Title plus margin
            for line in clean_lines:
                max_len = max(max_len, len(line) + (padding * 2))
            
            # Set width with some extra space
            width = min(max_len + 4, terminal_width - 2)
        
        # Ensure minimum width
        width = max(width, len(title) + 12)
        
        # Build the box
        result = []
        
        # Top border with centered title
        inner_width = width - 2
        title_with_spaces = f" {title} "
        title_len = len(title_with_spaces)
        
        if title_len < inner_width - 4:
            # Center the title with decorative elements
            side_len = (inner_width - title_len - 2) // 2
            left_side = chars['h'] * side_len + chars['dot']
            right_side = chars['dot'] + chars['h'] * (inner_width - title_len - len(left_side) - 1)
            title_line = f"{left_side}{title_with_spaces}{right_side}"
        else:
            # Simple centered title if too long
            padding_len = (inner_width - title_len) // 2
            title_line = f"{chars['h'] * padding_len}{title_with_spaces}{chars['h'] * (inner_width - title_len - padding_len)}"
        
        result.append(f"{chars['tl']}{title_line}{chars['tr']}")
        
        # Add a decorative separator line after title
        result.append(f"{chars['v']}{' ' * inner_width}{chars['v']}")
        
        # Process content lines
        formatted_lines = []
        for i, (line, clean_line) in enumerate(zip(lines, clean_lines)):
            original_line = line
            # Format specific patterns
            if "Logging initialized" in line:
                line = DisplayBox._format_logging_line(line)
            elif "Execution ID:" in line:
                line = DisplayBox._format_execution_line(line)
            elif "Log file:" in line:
                line = DisplayBox._format_logfile_line(line)
            elif "STARTING MODEL VERIFICATION" in line:
                line = DisplayBox._format_verification_start(line)
            elif "✓" in line:
                line = DisplayBox._format_success_line(line)
            
            # Recalculate clean line after formatting
            formatted_clean = ansi_escape.sub('', line)
            formatted_lines.append((line, formatted_clean))
        
        # Add content lines with improved spacing
        for i, (line, clean_line) in enumerate(formatted_lines):
            # Calculate padding for centering if requested
            if center_content:
                line_padding = (inner_width - len(clean_line)) // 2
                padded_line = f"{' ' * line_padding}{line}{' ' * (inner_width - len(clean_line) - line_padding)}"
            else:
                # Left-aligned with padding
                padded_line = f"{' ' * padding}{line}"
                # Account for ANSI codes when padding
                padding_needed = inner_width - len(clean_line) - padding
                padded_line = padded_line + ' ' * padding_needed
            
            result.append(f"{chars['v']}{padded_line}{chars['v']}")
        
        # Add spacing before bottom
        result.append(f"{chars['v']}{' ' * inner_width}{chars['v']}")
        
        # Bottom border
        result.append(f"{chars['bl']}{chars['h'] * inner_width}{chars['br']}")
        
        return '\n'.join(result)
    
    @staticmethod
    def _format_logging_line(line: str) -> str:
        """Format logging initialization line."""
        # Extract level
        if "Level:" in line:
            parts = line.split("Level:")
            if len(parts) == 2:
                return f"📊 {parts[0].strip()} Level: \033[32m{parts[1].strip()}\033[0m"
        return line
    
    @staticmethod
    def _format_execution_line(line: str) -> str:
        """Format execution ID line."""
        if "Execution ID:" in line:
            parts = line.split(":", 1)
            if len(parts) == 2:
                return f"🔖 {parts[0]}: \033[36m{parts[1].strip()}\033[0m"
        return line
    
    @staticmethod
    def _format_logfile_line(line: str) -> str:
        """Format log file path line."""
        if "Log file:" in line:
            parts = line.split(":", 1)
            if len(parts) == 2:
                # Shorten path if too long
                path = parts[1].strip()
                if len(path) > 50:
                    # Show only filename and parent directory
                    path_parts = path.split('/')
                    if len(path_parts) > 2:
                        path = f".../{'/'.join(path_parts[-2:])}"
                return f"📁 {parts[0]}: \033[90m{path}\033[0m"
        return line
    
    @staticmethod
    def _format_verification_start(line: str) -> str:
        """Format verification start line."""
        # Remove timestamp and INFO tags
        clean_line = re.sub(r'\[.*?\]', '', line).strip()
        clean_line = clean_line.replace('[INFO]', '').strip()
        if "STARTING MODEL VERIFICATION" in clean_line:
            return f"🔍 {clean_line.replace('===', '').strip()}"
        return line
    
    @staticmethod
    def _format_success_line(line: str) -> str:
        """Format success lines with check marks."""
        # Remove timestamp and INFO tags
        clean_line = re.sub(r'\[.*?\]', '', line).strip()
        clean_line = clean_line.replace('[INFO]', '').strip()
        # Already has checkmark, just clean it up
        return f"  {clean_line}"
    
    @staticmethod
    def create_simple_box(lines: List[str], width: Optional[int] = None) -> str:
        """Create a simple bordered box without title.
        
        Args:
            lines: Lines of content to display
            width: Box width (auto-detected if None)
            
        Returns:
            String representation of the box
        """
        # Get terminal width
        terminal_width = shutil.get_terminal_size().columns
        
        # Calculate box width
        if width is None:
            max_len = max(len(line) for line in lines) if lines else 20
            width = min(max_len + 4, terminal_width - 2)
        
        # Build the box
        result = []
        
        # Top border
        result.append(f"╭{'─' * (width - 2)}╮")
        
        # Content lines
        for line in lines:
            # Truncate if too long
            if len(line) > width - 4:
                line = line[:width - 7] + "..."
            
            # Center the line
            padded_line = line.center(width - 2)
            result.append(f"│{padded_line}│")
        
        # Bottom border
        result.append(f"╰{'─' * (width - 2)}╯")
        
        return '\n'.join(result)
    
    @staticmethod
    def create_corporate_header(title: str, version: str = "v1.0.0", width: int = 80) -> str:
        """Create a corporate-style header.
        
        Args:
            title: Main title text
            version: Version string
            width: Total width of the header
            
        Returns:
            Formatted header string
        """
        lines = []
        lines.append("=" * width)
        # Center the title with version
        title_with_version = f"{title.upper()} {version}"
        lines.append(title_with_version.center(width))
        lines.append("=" * width)
        return '\n'.join(lines)
    
    @staticmethod
    def create_corporate_section(title: str, content: Dict[str, str], width: int = 80) -> str:
        """Create a corporate-style section with key-value pairs.
        
        Args:
            title: Section title
            content: Dictionary of key-value pairs to display
            width: Total width of the section
            
        Returns:
            Formatted section string
        """
        lines = []
        lines.append("")  # Empty line before section
        lines.append(title.upper())
        lines.append("-" * width)
        
        # Find the longest key for alignment
        if content:
            max_key_length = max(len(key) for key in content.keys())
            # Add padding
            max_key_length += 2
            
            for key, value in content.items():
                formatted_key = f"  {key}".ljust(max_key_length + 2)
                lines.append(f"{formatted_key}: {value}")
        
        return '\n'.join(lines)
    
    @staticmethod
    def create_corporate_footer(width: int = 80) -> str:
        """Create a corporate-style footer.
        
        Args:
            width: Total width of the footer
            
        Returns:
            Formatted footer string
        """
        return "\n" + "=" * width