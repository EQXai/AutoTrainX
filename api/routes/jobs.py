"""
Jobs routes - Read-only access to job statistics.

These routes provide read-only access to job information and statistics
from the PostgreSQL database. No modifications are made - only SELECT queries.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from ..models.simple_schemas import (
    JobInfo,
    JobsListResponse,
    RunningJobsResponse,
    StatisticsResponse
)
from ..services.stats_reader import StatsReader

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize stats reader
stats_reader = StatsReader()


@router.get(
    "/{job_id}",
    response_model=JobInfo,
    summary="Get job information by ID",
    description="Retrieve information about a specific job from the database."
)
async def get_job(job_id: str) -> JobInfo:
    """Get job by ID."""
    try:
        job = await stats_reader.get_job_by_id(job_id)
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        
        return JobInfo(**job)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve job information: {str(e)}"
        )


@router.get(
    "",
    response_model=JobsListResponse,
    summary="List jobs with pagination and filtering",
    description="Get a paginated list of jobs with optional filtering by status and mode."
)
async def list_jobs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by job status"),
    mode: Optional[str] = Query(None, description="Filter by pipeline mode")
) -> JobsListResponse:
    """List jobs with pagination."""
    try:
        offset = (page - 1) * page_size
        
        jobs, total = await stats_reader.get_jobs_list(
            limit=page_size,
            offset=offset,
            status=status,
            mode=mode
        )
        
        return JobsListResponse(
            jobs=[JobInfo(**job) for job in jobs],
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve jobs list: {str(e)}"
        )


@router.get(
    "/running",
    response_model=RunningJobsResponse,
    summary="Get currently running jobs",
    description="Retrieve all jobs that are currently in progress."
)
async def get_running_jobs() -> RunningJobsResponse:
    """Get running jobs."""
    try:
        jobs = await stats_reader.get_running_jobs()
        
        return RunningJobsResponse(
            running_jobs=[JobInfo(**job) for job in jobs],
            count=len(jobs)
        )
        
    except Exception as e:
        logger.error(f"Failed to get running jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve running jobs: {str(e)}"
        )


@router.get(
    "/statistics",
    response_model=StatisticsResponse,
    summary="Get job statistics",
    description="Retrieve overall statistics about jobs, presets, and recent activity."
)
async def get_statistics() -> StatisticsResponse:
    """Get job statistics."""
    try:
        job_stats = await stats_reader.get_job_statistics()
        preset_stats = await stats_reader.get_preset_statistics()
        recent_completions = await stats_reader.get_recent_completions(limit=10)
        
        return StatisticsResponse(
            job_statistics=job_stats,
            preset_statistics=preset_stats,
            recent_completions=[JobInfo(**job) for job in recent_completions]
        )
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )


@router.get(
    "/health",
    summary="Check database connection health",
    description="Verify that the stats reader can connect to the database."
)
async def health_check():
    """Check database health."""
    try:
        # Try a simple query
        job_stats = await stats_reader.get_job_statistics()
        
        return {
            "status": "healthy",
            "message": "Database connection is working",
            "total_jobs": job_stats.get("total_jobs", 0)
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }