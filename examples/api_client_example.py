#!/usr/bin/env python3
"""
AutoTrainX API Client Example

This example demonstrates how to interact with the AutoTrainX FastAPI backend
for common operations like creating jobs, monitoring progress, and managing datasets.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

import httpx
import websockets

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AutoTrainXAPIClient:
    """Client for interacting with AutoTrainX API."""
    
    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 30):
        """
        Initialize the API client.
        
        Args:
            base_url: Base URL of the API server
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/api/v1"
        self.ws_base = self.base_url.replace('http', 'ws')
        self.timeout = timeout
    
    async def health_check(self) -> Dict[str, Any]:
        """Check API health status."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get training system status."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.api_base}/training/status")
            response.raise_for_status()
            return response.json()
    
    async def list_datasets(self, dataset_type: Optional[str] = None) -> Dict[str, Any]:
        """List available datasets."""
        params = {}
        if dataset_type:
            params['dataset_type'] = dataset_type
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.api_base}/datasets/", params=params)
            response.raise_for_status()
            return response.json()
    
    async def list_presets(self) -> Dict[str, Any]:
        """List available presets."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.api_base}/presets/")
            response.raise_for_status()
            return response.json()
    
    async def create_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new training job."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.api_base}/jobs/", json=job_data)
            response.raise_for_status()
            return response.json()
    
    async def get_job(self, job_id: str) -> Dict[str, Any]:
        """Get job details."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.api_base}/jobs/{job_id}")
            response.raise_for_status()
            return response.json()
    
    async def start_job(self, job_id: str) -> Dict[str, Any]:
        """Start job execution."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.api_base}/jobs/{job_id}/start")
            response.raise_for_status()
            return response.json()
    
    async def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel job execution."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.api_base}/jobs/{job_id}/cancel")
            response.raise_for_status()
            return response.json()
    
    async def list_jobs(self, status_filter: Optional[str] = None, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """List jobs with optional filtering."""
        params = {"page": page, "page_size": page_size}
        if status_filter:
            params['status_filter'] = status_filter
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.api_base}/jobs/", params=params)
            response.raise_for_status()
            return response.json()
    
    async def quick_start_training(self, source_path: str, preset: str = "FluxLORA", 
                                 dataset_name: Optional[str] = None) -> Dict[str, Any]:
        """Quick start training with minimal configuration."""
        params = {
            "source_path": source_path,
            "preset": preset,
            "auto_start": True
        }
        if dataset_name:
            params['dataset_name'] = dataset_name
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.api_base}/training/quick-start", params=params)
            response.raise_for_status()
            return response.json()
    
    async def start_single_training(self, source_path: str, preset: str, **kwargs) -> Dict[str, Any]:
        """Start single dataset training."""
        training_data = {
            "source_path": source_path,
            "preset": preset,
            "enable_monitoring": True,
            **kwargs
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.api_base}/training/single", json=training_data)
            response.raise_for_status()
            return response.json()
    
    async def monitor_job_progress(self, job_id: str, callback=None) -> None:
        """Monitor job progress via WebSocket."""
        uri = f"{self.ws_base}/ws/progress/{job_id}"
        
        try:
            logger.info(f"Connecting to WebSocket: {uri}")
            async with websockets.connect(uri) as websocket:
                logger.info(f"Connected to job {job_id} progress stream")
                
                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)
                        
                        if callback:
                            await callback(data)
                        else:
                            await self._default_progress_handler(data)
                        
                        # Check if job is finished
                        if data.get("type") == "progress_update":
                            progress_data = data.get("data", {})
                            if progress_data.get("status") in ["completed", "failed", "cancelled"]:
                                logger.info(f"Job {job_id} finished with status: {progress_data.get('status')}")
                                break
                                
                    except websockets.exceptions.ConnectionClosed:
                        logger.info("WebSocket connection closed")
                        break
                    except json.JSONDecodeError:
                        logger.error("Failed to decode WebSocket message")
                        
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
    
    async def _default_progress_handler(self, data: Dict[str, Any]) -> None:
        """Default progress handler for WebSocket messages."""
        message_type = data.get("type", "unknown")
        
        if message_type == "connection_established":
            logger.info("WebSocket connection established")
            
        elif message_type == "progress_update":
            progress = data.get("data", {})
            job_id = progress.get("job_id", "unknown")
            status = progress.get("status", "unknown")
            percentage = progress.get("progress_percentage", 0)
            current_step = progress.get("current_step", "")
            
            logger.info(f"Job {job_id}: {status} - {percentage:.1f}% - {current_step}")
            
            # Show additional training info if available
            if progress.get("epoch") is not None:
                epoch = progress.get("epoch")
                loss = progress.get("loss")
                logger.info(f"  Epoch: {epoch}, Loss: {loss:.4f}" if loss else f"  Epoch: {epoch}")
                
        elif message_type == "job_status":
            status_data = data.get("data", {})
            job_id = status_data.get("job_id", "unknown")
            status = status_data.get("status", "unknown")
            message = status_data.get("message", "")
            
            logger.info(f"Job {job_id} status changed to: {status} - {message}")
            
        else:
            logger.info(f"Received {message_type} message: {data}")


# Example usage functions

async def example_health_check():
    """Example: Check API health."""
    logger.info("=== Health Check Example ===")
    
    client = AutoTrainXAPIClient()
    
    try:
        health = await client.health_check()
        logger.info(f"API Health: {health['status']}")
        
        system_status = await client.get_system_status()
        logger.info(f"System Status: {system_status.get('system_status', 'unknown')}")
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")


async def example_list_resources():
    """Example: List datasets and presets."""
    logger.info("=== List Resources Example ===")
    
    client = AutoTrainXAPIClient()
    
    try:
        # List datasets
        datasets = await client.list_datasets()
        logger.info(f"Found {datasets['total_count']} datasets")
        for dataset in datasets['items'][:3]:  # Show first 3
            logger.info(f"  - {dataset['name']}: {dataset['total_images']} images")
        
        # List presets
        presets = await client.list_presets()
        logger.info(f"Found {len(presets['presets'])} presets")
        for preset in presets['presets'][:3]:  # Show first 3
            logger.info(f"  - {preset['name']}: {preset['description']}")
            
    except Exception as e:
        logger.error(f"Failed to list resources: {e}")


async def example_create_and_monitor_job():
    """Example: Create job and monitor progress."""
    logger.info("=== Create and Monitor Job Example ===")
    
    client = AutoTrainXAPIClient()
    
    try:
        # Create a job (you'll need to adjust the source_path)
        job_data = {
            "mode": "single",
            "name": "Example Training Job",
            "description": "API client example job",
            "source_path": "/path/to/your/dataset",  # Adjust this path
            "preset": "FluxLORA",
            "repeats": 30,
            "class_name": "person",
            "generate_configs": True,
            "auto_clean": False,
            "enable_preview": True
        }
        
        logger.info("Creating job...")
        job = await client.create_job(job_data)
        job_id = job['id']
        logger.info(f"Created job: {job_id}")
        
        # Start the job
        logger.info("Starting job...")
        await client.start_job(job_id)
        
        # Monitor progress
        logger.info("Monitoring job progress...")
        await client.monitor_job_progress(job_id)
        
        # Get final job status
        final_job = await client.get_job(job_id)
        logger.info(f"Final job status: {final_job['status']}")
        
    except Exception as e:
        logger.error(f"Job creation/monitoring failed: {e}")


async def example_quick_start():
    """Example: Quick start training."""
    logger.info("=== Quick Start Example ===")
    
    client = AutoTrainXAPIClient()
    
    try:
        # Quick start training (adjust the source_path)
        source_path = "/path/to/your/dataset"  # Adjust this path
        
        logger.info(f"Quick starting training for: {source_path}")
        result = await client.quick_start_training(
            source_path=source_path,
            preset="FluxLORA",
            dataset_name="example_dataset"
        )
        
        job_id = result['job_id']
        logger.info(f"Started job: {job_id}")
        
        # Monitor the job
        await client.monitor_job_progress(job_id)
        
    except Exception as e:
        logger.error(f"Quick start failed: {e}")


async def example_list_jobs():
    """Example: List and manage jobs."""
    logger.info("=== List Jobs Example ===")
    
    client = AutoTrainXAPIClient()
    
    try:
        # List all jobs
        jobs = await client.list_jobs()
        logger.info(f"Found {jobs['total_count']} total jobs")
        
        for job in jobs['items']:
            logger.info(f"  Job {job['id']}: {job['status']} - {job['name'] or 'Unnamed'}")
        
        # List only running jobs
        running_jobs = await client.list_jobs(status_filter="running")
        logger.info(f"Found {running_jobs['total_count']} running jobs")
        
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")


async def main():
    """Run all examples."""
    logger.info("AutoTrainX API Client Examples")
    logger.info("=" * 50)
    
    # Check if API server is running
    try:
        client = AutoTrainXAPIClient()
        await client.health_check()
        logger.info("API server is running, proceeding with examples...")
    except Exception as e:
        logger.error(f"API server is not accessible: {e}")
        logger.error("Please start the API server first: python api_server.py --dev")
        return
    
    # Run examples
    await example_health_check()
    print()
    
    await example_list_resources()
    print()
    
    await example_list_jobs()
    print()
    
    # Uncomment these if you have datasets available
    # await example_quick_start()
    # print()
    # 
    # await example_create_and_monitor_job()
    
    logger.info("Examples completed!")


if __name__ == "__main__":
    # Install required packages first:
    # pip install httpx websockets
    
    asyncio.run(main())