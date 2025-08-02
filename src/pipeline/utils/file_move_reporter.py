"""
Reporter for file move operations to provide user feedback.
"""

from typing import Dict, Any, List
from pathlib import Path


class FileMoveReporter:
    """Formats and reports file move operation results."""
    
    # Display style options
    STYLE_ULTRA_COMPACT = 'ultra_compact'
    STYLE_COMPACT = 'compact'
    STYLE_DETAILED = 'detailed'
    STYLE_INLINE = 'inline'
    STYLE_MINIMAL = 'minimal'
    
    @staticmethod
    def report_results(results: List[Dict[str, Any]], mode: str = 'console',
                      verbose: bool = True, style: str = None) -> str:
        """
        Format file move results for display.
        
        Args:
            results: List of file move results
            mode: Output mode ('console', 'json', 'compact')
            verbose: Whether to show detailed information
            style: Display style (overrides mode/verbose)
            
        Returns:
            Formatted string for display
        """
        if not results:
            return ""
            
        if mode == 'json':
            import json
            return json.dumps(results, indent=2)
            
        # Determine which formatter to use
        if style == FileMoveReporter.STYLE_ULTRA_COMPACT:
            return FileMoveReporter._format_ultra_compact(results)
        elif style == FileMoveReporter.STYLE_MINIMAL:
            return FileMoveReporter._format_minimal(results)
        elif style == FileMoveReporter.STYLE_INLINE:
            return FileMoveReporter._format_inline(results)
        elif mode == 'compact' or not verbose:
            return FileMoveReporter._format_compact(results)
        else:  # console mode with verbose
            return FileMoveReporter._format_detailed(results)
                
    @staticmethod
    def _format_detailed(results: List[Dict[str, Any]]) -> str:
        """Format detailed results for console output."""
        lines = []
        
        for result in results:
            if result.get('success'):
                lines.append(f"\n✅ Files moved to custom location: {result['destination']}")
                lines.append(f"   Model name: {result['model_name']}")
                
                moved = result.get('moved_files', {})
                
                # Model files
                if moved.get('models'):
                    lines.append(f"   • Model files: {len(moved['models'])} moved")
                    for model in moved['models']:
                        size_mb = model['size'] / (1024 * 1024)
                        lines.append(f"     - {Path(model['source']).name} ({size_mb:.1f} MB)")
                        
                # Config files
                if moved.get('configs'):
                    lines.append(f"   • Configuration files: {len(moved['configs'])} copied")
                    for config in moved['configs']:
                        lines.append(f"     - {Path(config['source']).name}")
                        
                # Preview folders
                if moved.get('previews'):
                    lines.append(f"   • Preview folders: {len(moved['previews'])} moved")
                    for preview in moved['previews']:
                        lines.append(f"     - Preview/ ({preview['file_count']} files)")
                        
            else:
                lines.append(f"\n❌ Failed to move files for {result['dataset_name']}")
                lines.append(f"   Error: {result.get('error', 'Unknown error')}")
                
        return '\n'.join(lines)
        
    @staticmethod
    def _format_compact(results: List[Dict[str, Any]]) -> str:
        """Format compact results for console output."""
        lines = []
        
        successful = [r for r in results if r.get('success')]
        failed = [r for r in results if not r.get('success')]
        
        if successful:
            for result in successful:
                moved = result.get('moved_files', {})
                
                # Calculate sizes and counts
                model_files = moved.get('models', [])
                total_size = sum(m.get('size', 0) for m in model_files)
                size_str = FileMoveReporter._format_size(total_size) if total_size > 0 else ""
                
                preview_count = sum(p.get('file_count', 0) for p in moved.get('previews', []))
                
                # Extract just the model name without path
                model_name = result.get('model_name', result.get('dataset_name', 'unknown'))
                
                # Format: Simple arrow with size and preview count
                line = f"  📦 {model_name} → custom/"
                
                # Add size and preview info if available
                info_parts = []
                if size_str:
                    info_parts.append(f"💾{size_str}")
                if preview_count > 0:
                    info_parts.append(f"🖼️{preview_count}")
                    
                if info_parts:
                    line += f" ({' '.join(info_parts)})"
                    
                lines.append(line)
                
        if failed:
            for result in failed:
                error_msg = result.get('error', 'Failed')
                # Truncate long error messages
                if len(error_msg) > 50:
                    error_msg = error_msg[:47] + "..."
                lines.append(f"  ❌ {result['dataset_name']}: {error_msg}")
                
        return '\n'.join(lines)
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes to human readable size."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f}TB"
        
    @staticmethod
    def _format_ultra_compact(results: List[Dict[str, Any]]) -> str:
        """Format ultra compact single-line results."""
        successful = [r for r in results if r.get('success')]
        failed_count = len([r for r in results if not r.get('success')])
        
        if not successful and failed_count == 0:
            return ""
            
        if len(successful) == 1 and failed_count == 0:
            # Single file format
            result = successful[0]
            moved = result.get('moved_files', {})
            model_files = moved.get('models', [])
            size = sum(m.get('size', 0) for m in model_files)
            size_str = FileMoveReporter._format_size(size) if size > 0 else ""
            preview_count = sum(p.get('file_count', 0) for p in moved.get('previews', []))
            
            info_parts = []
            if size_str:
                info_parts.append(size_str)
            if preview_count > 0:
                info_parts.append(f"{preview_count}img")
                
            info = f" ({', '.join(info_parts)})" if info_parts else ""
            return f"  → {result.get('model_name', 'model')} [custom]{info}"
        else:
            # Multiple files summary
            total_size = 0
            for r in successful:
                moved = r.get('moved_files', {})
                model_files = moved.get('models', [])
                total_size += sum(m.get('size', 0) for m in model_files)
                
            size_str = FileMoveReporter._format_size(total_size) if total_size > 0 else ""
            
            summary = f"  → Moved {len(successful)} models"
            if size_str:
                summary += f" ({size_str})"
            if failed_count > 0:
                summary += f" • {failed_count} failed"
                
            return summary
    
    @staticmethod
    def _format_minimal(results: List[Dict[str, Any]]) -> str:
        """Format minimal results - just the essentials."""
        lines = []
        
        for result in results:
            if result.get('success'):
                model_name = result.get('model_name', result.get('dataset_name', 'unknown'))
                # Truncate long names
                if len(model_name) > 20:
                    model_name = model_name[:17] + "..."
                lines.append(f"  → {model_name}")
            else:
                dataset = result.get('dataset_name', 'unknown')
                if len(dataset) > 20:
                    dataset = dataset[:17] + "..."
                lines.append(f"  ✗ {dataset}")
                
        return '\n'.join(lines)
    
    @staticmethod
    def _format_inline(results: List[Dict[str, Any]]) -> str:
        """Format inline results for batch display."""
        successful = [r for r in results if r.get('success')]
        failed = [r for r in results if not r.get('success')]
        
        if not successful and not failed:
            return ""
            
        # Create inline summary
        parts = []
        if successful:
            parts.append(f"✓{len(successful)}")
        if failed:
            parts.append(f"✗{len(failed)}")
            
        return f"  [File Move: {' '.join(parts)}]"
    
    @staticmethod
    def report_summary(summary: Dict[str, Any]) -> str:
        """
        Format summary of all file move operations.
        
        Args:
            summary: Summary dictionary from file move hook
            
        Returns:
            Formatted summary string
        """
        if not summary:
            return ""
            
        total = summary.get('total_datasets', 0)
        successful = summary.get('successful_moves', 0)
        failed = summary.get('failed_moves', 0)
        rate = summary.get('success_rate', '0%')
        
        if total == 0:
            return ""
            
        lines = [
            "\n" + "="*50,
            "📁 File Move Summary",
            "="*50,
            f"Total datasets processed: {total}",
            f"Successfully moved: {successful}",
            f"Failed to move: {failed}",
            f"Success rate: {rate}",
            "="*50
        ]
        
        return '\n'.join(lines)