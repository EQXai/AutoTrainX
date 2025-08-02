"""JobID generation utilities for AutoTrainX."""

import uuid


def generate_job_id() -> str:
    """Generate a unique 8-character JobID.
    
    Returns:
        str: An 8-character unique identifier (e.g., 'a2862f3d')
    """
    return str(uuid.uuid4())[:8]