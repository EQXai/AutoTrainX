"""
Utility functions for ImagePreview module.
"""

import subprocess
import time
import requests
from pathlib import Path
from typing import Optional, Tuple
import logging

from ..config import Config

logger = logging.getLogger(__name__)


class ComfyUIManager:
    """Manages ComfyUI process and connection."""
    
    @staticmethod
    def find_available_port(start_port: int = 8188, max_attempts: int = 10) -> int:
        """
        Find an available port starting from start_port.
        
        Args:
            start_port: Port to start checking from
            max_attempts: Maximum number of ports to check
            
        Returns:
            Available port number, or start_port if none found
        """
        import socket
        
        for port in range(start_port, start_port + max_attempts):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                
                if result != 0:  # Port is available
                    return port
            except Exception:
                continue
                
        logger.warning(f"Could not find available port in range {start_port}-{start_port + max_attempts - 1}")
        return start_port  # Return original port as fallback
    
    @staticmethod
    def diagnose_comfyui_environment(comfyui_path: str) -> dict:
        """
        Diagnose ComfyUI environment for debugging.
        
        Args:
            comfyui_path: Path to ComfyUI installation
            
        Returns:
            Dictionary with diagnostic information
        """
        diagnosis = {
            "comfyui_path_exists": False,
            "main_py_exists": False,
            "python_executable": None,
            "requirements_exist": False,
            "venv_detected": False,
            "gpu_available": False,
            "port_available": False,
            "errors": []
        }
        
        try:
            comfyui_dir = Path(comfyui_path)
            diagnosis["comfyui_path_exists"] = comfyui_dir.exists()
            
            if comfyui_dir.exists():
                main_py = comfyui_dir / "main.py"
                diagnosis["main_py_exists"] = main_py.exists()
                
                # Check for requirements
                req_files = ["requirements.txt", "requirements-cuda.txt"]
                diagnosis["requirements_exist"] = any((comfyui_dir / req).exists() for req in req_files)
                
                # Check for virtual environment
                venv_indicators = ["venv", ".venv", "env", ".env"]
                venv_path = None
                for venv_name in venv_indicators:
                    potential_venv = comfyui_dir / venv_name
                    if potential_venv.exists() and (potential_venv / "bin" / "activate").exists():
                        venv_path = potential_venv
                        break
                
                diagnosis["venv_detected"] = venv_path is not None
                diagnosis["venv_path"] = str(venv_path) if venv_path else None
                
            # Check Python executable
            try:
                result = subprocess.run(["python", "--version"], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    diagnosis["python_executable"] = result.stdout.strip()
            except Exception as e:
                diagnosis["errors"].append(f"Python check failed: {e}")
                
            # Check GPU availability
            try:
                import torch
                diagnosis["gpu_available"] = torch.cuda.is_available()
            except ImportError:
                diagnosis["errors"].append("PyTorch not available to check GPU")
            except Exception as e:
                diagnosis["errors"].append(f"GPU check failed: {e}")
                
            # Check port availability
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('127.0.0.1', 8188))
                sock.close()
                diagnosis["port_available"] = result != 0  # Port available if connection fails
            except Exception as e:
                diagnosis["errors"].append(f"Port check failed: {e}")
                
        except Exception as e:
            diagnosis["errors"].append(f"General diagnosis failed: {e}")
            
        return diagnosis
    
    @staticmethod
    def ensure_comfyui_running(comfyui_url: str = "http://127.0.0.1:8188", 
                              timeout: int = 60) -> Tuple[bool, str]:  # Return tuple with URL
        """
        Ensure ComfyUI is running and accessible.
        
        Args:
            comfyui_url: URL to check ComfyUI
            timeout: Maximum time to wait for ComfyUI to start
            
        Returns:
            Tuple of (success, actual_url_used)
        """
        # First check if already running
        if ComfyUIManager.is_comfyui_running(comfyui_url):
            return True, comfyui_url
            
        # Try to start ComfyUI
        comfyui_path = Config.get_comfyui_path()
        if not comfyui_path:
            logger.warning("ComfyUI path not configured. Please run with --comfyui-path")
            return False, comfyui_url
        
        # Diagnose ComfyUI environment
        diagnosis = ComfyUIManager.diagnose_comfyui_environment(comfyui_path)
        
        # Log diagnosis for debugging
        logger.info("ComfyUI Environment Diagnosis:")
        logger.info(f"  ComfyUI path exists: {diagnosis['comfyui_path_exists']}")
        logger.info(f"  main.py exists: {diagnosis['main_py_exists']}")
        logger.info(f"  Python: {diagnosis['python_executable']}")
        logger.info(f"  GPU available: {diagnosis['gpu_available']}")
        logger.info(f"  Port 8188 available: {diagnosis['port_available']}")
        
        if diagnosis['errors']:
            logger.warning("Diagnosis errors:")
            for error in diagnosis['errors']:
                logger.warning(f"  {error}")
        
        if not diagnosis['comfyui_path_exists']:
            logger.error(f"ComfyUI directory not found: {comfyui_path}")
            return False, comfyui_url
            
        if not diagnosis['main_py_exists']:
            logger.error(f"ComfyUI main.py not found in: {comfyui_path}")
            return False, comfyui_url
            
        comfyui_dir = Path(comfyui_path)
        main_py = comfyui_dir / "main.py"
            
        logger.info(f"Starting ComfyUI from: {comfyui_dir}")
        
        try:
            # Find available port
            available_port = ComfyUIManager.find_available_port(8188)
            actual_url = f"http://127.0.0.1:{available_port}"
            
            if available_port != 8188:
                logger.info(f"Port 8188 is in use, using port {available_port} instead")
            
            # If port 8188 is in use but ComfyUI isn't responding, try to clean it up
            if available_port != 8188:
                try:
                    subprocess.run(["pkill", "-f", "main.py.*8188"], check=False)
                    time.sleep(2)
                    # Recheck if port 8188 is now available
                    if ComfyUIManager.find_available_port(8188, 1) == 8188:
                        available_port = 8188
                        actual_url = f"http://127.0.0.1:{available_port}"
                        logger.info("Port 8188 is now available after cleanup")
                except:
                    pass
            
            # Detect and use ComfyUI's virtual environment
            python_executable = "python"
            if diagnosis['venv_detected'] and diagnosis.get('venv_path'):
                venv_python = Path(diagnosis['venv_path']) / "bin" / "python"
                if venv_python.exists():
                    python_executable = str(venv_python)
                    logger.info(f"Using ComfyUI virtual environment: {diagnosis['venv_path']}")
                else:
                    logger.warning(f"Virtual environment detected but python executable not found: {venv_python}")
            
            # Create ComfyUI log file
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            comfyui_log_dir = Path.cwd() / "logs" / "ComfyUI_log"
            comfyui_log_dir.mkdir(parents=True, exist_ok=True)
            log_file_path = comfyui_log_dir / f"comfyui_{timestamp}.log"
            log_file = open(log_file_path, 'w', buffering=1)
            
            logger.info(f"ComfyUI output will be logged to: {log_file_path}")
            
            # Start ComfyUI in background with better logging
            logger.info(f"Executing command: {python_executable} main.py --listen 127.0.0.1 --port {available_port}")
            process = subprocess.Popen(
                [python_executable, str(main_py), "--listen", "127.0.0.1", "--port", str(available_port)],
                cwd=str(comfyui_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Monitor startup with output logging
            start_time = time.time()
            startup_logs = []
            
            while time.time() - start_time < timeout:
                # Check if ComfyUI is responding
                if ComfyUIManager.is_comfyui_running(actual_url):
                    logger.info(f"ComfyUI started successfully on {actual_url}")
                    
                    # Start background thread to continue logging
                    import threading
                    def log_output():
                        try:
                            while process.poll() is None:
                                line = process.stdout.readline()
                                if line:
                                    log_file.write(line)
                                    log_file.flush()
                        except Exception as e:
                            logger.debug(f"Error in ComfyUI log thread: {e}")
                        finally:
                            log_file.close()
                    
                    log_thread = threading.Thread(target=log_output, daemon=True)
                    log_thread.start()
                    
                    return True, actual_url
                
                # Read some output for debugging
                try:
                    import select
                    if process.poll() is None:  # Process is still running
                        # Check if there's output to read
                        ready, _, _ = select.select([process.stdout], [], [], 0.1)
                        if ready:
                            line = process.stdout.readline()
                            if line:
                                startup_logs.append(line.strip())
                                # Write to log file
                                log_file.write(line)
                                log_file.flush()
                                # Look for important messages
                                if "server running" in line.lower():
                                    logger.info(f"ComfyUI startup: {line.strip()}")
                                elif "error" in line.lower():
                                    logger.warning(f"ComfyUI error: {line.strip()}")
                except:
                    pass
                
                # Check if process died
                if process.poll() is not None:
                    logger.error(f"ComfyUI process exited with code: {process.poll()}")
                    break
                    
                time.sleep(1)
                
            # If we get here, startup failed
            logger.error("ComfyUI failed to start within timeout")
            
            # Log recent output for debugging
            if startup_logs:
                logger.error("Recent ComfyUI output:")
                for log in startup_logs[-10:]:  # Last 10 lines
                    logger.error(f"  {log}")
            
            # Try to get remaining output
            try:
                remaining_output, _ = process.communicate(timeout=2)
                if remaining_output:
                    logger.error(f"ComfyUI final output: {remaining_output}")
                    log_file.write(f"\n--- ERROR: ComfyUI failed to start ---\n")
                    log_file.write(remaining_output)
            except:
                pass
            finally:
                # Close log file
                log_file.close()
                
            process.terminate()
            return False, actual_url
            
        except Exception as e:
            logger.error(f"Failed to start ComfyUI: {e}")
            # Close log file if it was opened
            if 'log_file' in locals() and not log_file.closed:
                log_file.write(f"\n--- ERROR: {e} ---\n")
                log_file.close()
            return False, comfyui_url
            
    @staticmethod
    def is_comfyui_running(comfyui_url: str) -> bool:
        """
        Check if ComfyUI is running at the given URL.
        
        Args:
            comfyui_url: URL to check
            
        Returns:
            True if running, False otherwise
        """
        try:
            response = requests.get(f"{comfyui_url}/system_stats", timeout=2)
            return response.status_code == 200
        except:
            return False
            
    @staticmethod
    def get_comfyui_models_path() -> Optional[Path]:
        """
        Get the path to ComfyUI models directory.
        
        Returns:
            Path to models directory or None if not found
        """
        comfyui_path = Config.get_comfyui_path()
        if not comfyui_path:
            return None
            
        models_path = Path(comfyui_path) / "models"
        if models_path.exists():
            return models_path
            
        return None
        
    @staticmethod
    def get_lora_path() -> Optional[Path]:
        """
        Get the path to ComfyUI LoRA models directory.
        
        Returns:
            Path to LoRA directory or None if not found
        """
        models_path = ComfyUIManager.get_comfyui_models_path()
        if not models_path:
            return None
            
        lora_path = models_path / "loras"
        if lora_path.exists():
            return lora_path
            
        return None
        
    @staticmethod
    def get_checkpoint_path() -> Optional[Path]:
        """
        Get the path to ComfyUI checkpoint models directory.
        
        Returns:
            Path to checkpoints directory or None if not found
        """
        models_path = ComfyUIManager.get_comfyui_models_path()
        if not models_path:
            return None
            
        checkpoint_path = models_path / "checkpoints"
        if checkpoint_path.exists():
            return checkpoint_path
            
        return None
    
    @staticmethod
    def shutdown_comfyui(server_url: str = "http://127.0.0.1:8188") -> bool:
        """
        Shutdown ComfyUI server gracefully.
        
        Args:
            server_url: URL of the ComfyUI server
            
        Returns:
            True if shutdown successful, False otherwise
        """
        try:
            # Try graceful shutdown via API
            response = requests.post(f"{server_url}/system/shutdown", timeout=5)
            if response.status_code == 200:
                logger.info("ComfyUI shutdown gracefully via API")
                return True
        except Exception as e:
            logger.debug(f"API shutdown failed: {e}, trying process kill")
        
        # Fallback: kill process by name
        try:
            import subprocess
            result = subprocess.run(
                ["pkill", "-f", "main.py.*--listen.*--port"], 
                capture_output=True, 
                text=True
            )
            if result.returncode == 0:
                logger.info("ComfyUI process killed successfully")
                return True
            else:
                logger.warning("No ComfyUI process found to kill")
                return True  # Consider it successful if nothing to kill
        except Exception as e:
            logger.error(f"Failed to kill ComfyUI process: {e}")
            return False