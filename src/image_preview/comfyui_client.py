"""
Client for interacting with ComfyUI API.
"""

import json
import time
import requests
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path
import uuid
from datetime import datetime

try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

logger = logging.getLogger(__name__)
if not WEBSOCKET_AVAILABLE:
    logger.warning("websocket-client not installed. Some ComfyUI features may be limited. Install with: pip install websocket-client")


class ComfyUIClient:
    """
    Client for sending workflows to ComfyUI and retrieving results.
    """
    
    def __init__(self, server_url: str = "http://127.0.0.1:8188"):
        """
        Initialize ComfyUI client.
        
        Args:
            server_url: URL of the ComfyUI server
        """
        self.server_url = server_url.rstrip('/')
        self.client_id = str(uuid.uuid4())
        self._validate_connection()
        
    def _validate_connection(self):
        """Validate connection to ComfyUI server."""
        try:
            response = requests.get(f"{self.server_url}/system_stats")
            response.raise_for_status()
            logger.info(f"Connected to ComfyUI server at {self.server_url}")
        except Exception as e:
            logger.debug(f"Could not connect to ComfyUI server: {e}")
            
    def execute_workflow(self, workflow: Dict[str, Any], dataset_name: Optional[str] = None) -> str:
        """
        Send workflow to ComfyUI for execution.
        
        Args:
            workflow: Workflow dictionary to execute
            dataset_name: Optional dataset name for logging purposes
            
        Returns:
            Job ID for tracking execution
        """
        # Save workflow to log directory before execution
        self._save_workflow_log(workflow, dataset_name)
        
        # Prepare prompt data
        prompt_data = {
            "prompt": workflow,
            "client_id": self.client_id
        }
        
        # Send to ComfyUI
        response = requests.post(
            f"{self.server_url}/prompt",
            json=prompt_data
        )
        response.raise_for_status()
        
        result = response.json()
        job_id = result.get('prompt_id')
        
        logger.info(f"Submitted workflow with job ID: {job_id}")
        return job_id
    
    def _save_workflow_log(self, workflow: Dict[str, Any], dataset_name: Optional[str] = None):
        """
        Save workflow to log directory for debugging purposes.
        
        Args:
            workflow: Workflow dictionary to save
            dataset_name: Optional dataset name for the filename
        """
        try:
            # Create workflow_log directory inside logs
            base_path = Path.cwd()
            log_dir = base_path / "logs" / "workflow_log"
            log_dir.mkdir(exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if dataset_name:
                filename = f"workflow_{dataset_name}_{timestamp}.json"
            else:
                filename = f"workflow_{timestamp}.json"
            
            # Save workflow
            log_path = log_dir / filename
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(workflow, f, indent=2)
            
            logger.debug(f"Saved workflow log to: {log_path}")
            
        except Exception as e:
            # Don't fail execution if logging fails
            logger.warning(f"Failed to save workflow log: {e}")
        
    def wait_for_completion(self, job_id: str, timeout: int = 300) -> List[bytes]:
        """
        Wait for workflow completion and retrieve generated images.
        
        Args:
            job_id: Job ID to monitor
            timeout: Maximum time to wait in seconds
            
        Returns:
            List of image data (bytes)
        """
        start_time = time.time()
        images = []
        
        # Connect to WebSocket for progress updates
        ws_url = f"ws://{self.server_url.replace('http://', '').replace('https://', '')}/ws?clientId={self.client_id}"
        
        try:
            # Poll for completion
            while time.time() - start_time < timeout:
                # Check execution status
                history = self.get_history(job_id)
                
                if history and job_id in history:
                    job_data = history[job_id]
                    
                    # Check if completed
                    if 'outputs' in job_data:
                        # Extract image data from outputs
                        for node_id, node_output in job_data['outputs'].items():
                            if 'images' in node_output:
                                for image_info in node_output['images']:
                                    image_data = self._download_image(
                                        image_info['filename'],
                                        image_info.get('subfolder', ''),
                                        image_info.get('type', 'output')
                                    )
                                    if image_data:
                                        images.append(image_data)
                        break
                        
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"Error waiting for completion: {e}")
            
        if not images:
            logger.warning(f"No images generated for job {job_id}")
            
        return images
        
    def get_history(self, job_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get execution history from ComfyUI.
        
        Args:
            job_id: Optional specific job ID to get history for
            
        Returns:
            History dictionary
        """
        try:
            if job_id:
                response = requests.get(f"{self.server_url}/history/{job_id}")
            else:
                response = requests.get(f"{self.server_url}/history")
                
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return {}
            
    def _download_image(self, filename: str, subfolder: str = "", 
                       image_type: str = "output") -> Optional[bytes]:
        """
        Download generated image from ComfyUI.
        
        Args:
            filename: Name of the image file
            subfolder: Subfolder path
            image_type: Type of image (output, input, temp)
            
        Returns:
            Image data as bytes or None if failed
        """
        try:
            params = {
                "filename": filename,
                "subfolder": subfolder,
                "type": image_type
            }
            
            response = requests.get(
                f"{self.server_url}/view",
                params=params
            )
            response.raise_for_status()
            
            return response.content
            
        except Exception as e:
            logger.debug(f"Could not download image {filename} via API (this is normal if image is saved locally): {e}")
            return None
            
    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get current queue status from ComfyUI.
        
        Returns:
            Queue status information
        """
        try:
            response = requests.get(f"{self.server_url}/queue")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            return {}
            
    def interrupt_execution(self):
        """
        Interrupt current execution in ComfyUI.
        """
        try:
            response = requests.post(f"{self.server_url}/interrupt")
            response.raise_for_status()
            logger.info("Interrupted ComfyUI execution")
        except Exception as e:
            logger.error(f"Failed to interrupt execution: {e}")
            
    def clear_queue(self):
        """
        Clear the execution queue in ComfyUI.
        """
        try:
            response = requests.post(
                f"{self.server_url}/queue",
                json={"clear": True}
            )
            response.raise_for_status()
            logger.info("Cleared ComfyUI queue")
        except Exception as e:
            logger.error(f"Failed to clear queue: {e}")