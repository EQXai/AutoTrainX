# AutoTrainX FastAPI Backend

A RESTful API backend for the AutoTrainX machine learning training pipeline, providing comprehensive endpoints for job management, training operations, dataset handling, and real-time progress monitoring.

## Features

- **Job Management**: Create, monitor, and manage training jobs with full CRUD operations
- **Training Operations**: Support for single, batch, and variations training modes
- **Dataset Management**: Upload, prepare, and organize training datasets
- **Preset Configuration**: Manage training presets and generate custom configurations
- **Real-time Progress**: WebSocket-based progress monitoring and status updates
- **Error Handling**: Comprehensive error responses and validation
- **Authentication Ready**: Structured for easy integration of authentication systems
- **Production Ready**: Includes logging, monitoring, and deployment configurations

## Architecture

### Core Components

1. **FastAPI Application** (`api/main.py`)
   - Application setup with CORS, middleware, and exception handlers
   - Route registration and OpenAPI documentation
   - Health checks and lifecycle management

2. **Route Handlers** (`api/routes/`)
   - `jobs.py`: Job management endpoints (CRUD operations)
   - `training.py`: Training execution endpoints for all modes
   - `datasets.py`: Dataset management and preparation
   - `presets.py`: Preset configuration and parameter management

3. **Business Logic** (`api/services/`)
   - `job_service.py`: Core business logic integrating with existing components
   - Async job execution and progress tracking
   - Integration with AutoTrainPipeline and DatabaseManager

4. **WebSocket Support** (`api/websockets/`)
   - `progress.py`: Real-time progress updates and job status notifications
   - Connection management for multiple clients
   - Broadcasting system for global and job-specific updates

5. **Data Models** (`api/models/`)
   - `schemas.py`: Pydantic models for request/response validation
   - Type-safe API contracts with comprehensive validation

6. **Infrastructure** (`api/`)
   - `dependencies.py`: Dependency injection for FastAPI
   - `exceptions.py`: Custom exception handling
   - `requirements.txt`: API-specific dependencies

## API Endpoints

### Job Management
- `POST /api/v1/jobs/` - Create new training job
- `GET /api/v1/jobs/` - List jobs with filtering and pagination
- `GET /api/v1/jobs/{job_id}` - Get job details
- `PATCH /api/v1/jobs/{job_id}` - Update job information
- `DELETE /api/v1/jobs/{job_id}` - Delete job
- `POST /api/v1/jobs/{job_id}/start` - Start job execution
- `POST /api/v1/jobs/{job_id}/cancel` - Cancel running job

### Training Operations
- `POST /api/v1/training/single` - Single dataset training
- `POST /api/v1/training/batch` - Batch training for multiple datasets
- `POST /api/v1/training/variations` - Parameter variations training
- `POST /api/v1/training/quick-start` - Quick start with minimal configuration
- `GET /api/v1/training/status` - Training system status
- `GET /api/v1/training/modes` - Available training modes

### Dataset Management
- `GET /api/v1/datasets/` - List available datasets
- `GET /api/v1/datasets/{dataset_name}` - Get dataset details
- `POST /api/v1/datasets/prepare` - Prepare dataset for training
- `DELETE /api/v1/datasets/{dataset_name}` - Delete dataset
- `GET /api/v1/datasets/{dataset_name}/files` - List dataset files
- `GET /api/v1/datasets/{dataset_name}/sample-prompts` - Get sample prompts

### Preset Management
- `GET /api/v1/presets/` - List available presets
- `GET /api/v1/presets/{preset_name}` - Get preset details
- `POST /api/v1/presets/generate-config` - Generate preset configuration
- `GET /api/v1/presets/{preset_name}/parameters` - Get preset parameters
- `GET /api/v1/presets/categories` - Get preset categories

### WebSocket Endpoints
- `WS /ws/progress` - Global progress updates
- `WS /ws/progress/{job_id}` - Job-specific progress updates

### System Endpoints
- `GET /health` - System health check
- `GET /` - API information
- `GET /docs` - Interactive API documentation
- `GET /openapi.json` - OpenAPI schema

## Installation and Setup

### 1. Install Dependencies

```bash
# Install API-specific dependencies
pip install -r api/requirements.txt

# Or install with main requirements
pip install -r requirements.txt
```

### 2. Environment Validation

The API server automatically validates the environment on startup and creates necessary directories:
- `DB/` - Database directory
- `workspace/` - Training workspace
- `logs/` - API logs

### 3. Start the Server

#### Development Mode
```bash
# Basic development server
python api_server.py --dev

# Custom host and port
python api_server.py --host 0.0.0.0 --port 8080 --dev

# With debug logging
python api_server.py --dev --log-level debug
```

#### Production Mode
```bash
# Production server with multiple workers
python api_server.py --prod --workers 4

# With SSL
python api_server.py --prod --ssl-keyfile key.pem --ssl-certfile cert.pem
```

#### Configuration Check
```bash
# Validate configuration without starting
python api_server.py --check-config
```

## Usage Examples

### 1. Create and Start a Training Job

```python
import httpx
import asyncio

async def create_job():
    async with httpx.AsyncClient() as client:
        # Create job
        job_data = {
            "mode": "single",
            "source_path": "/path/to/dataset",
            "preset": "FluxLORA",
            "name": "My Training Job"
        }
        
        response = await client.post("http://localhost:8000/api/v1/jobs/", json=job_data)
        job = response.json()
        job_id = job["id"]
        
        # Start job
        await client.post(f"http://localhost:8000/api/v1/jobs/{job_id}/start")
        
        return job_id
```

### 2. Monitor Progress via WebSocket

```python
import websockets
import json
import asyncio

async def monitor_progress(job_id):
    uri = f"ws://localhost:8000/ws/progress/{job_id}"
    
    async with websockets.connect(uri) as websocket:
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            
            if data["type"] == "progress_update":
                progress = data["data"]
                print(f"Progress: {progress['progress_percentage']:.1f}% - {progress['current_step']}")
                
                if progress["status"] in ["completed", "failed", "cancelled"]:
                    break

# Usage
asyncio.run(monitor_progress("job-id-here"))
```

### 3. Quick Training Start

```python
async def quick_train():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/training/quick-start",
            params={
                "source_path": "/path/to/dataset",
                "preset": "FluxLORA",
                "auto_start": True
            }
        )
        return response.json()
```

## Integration with Existing Codebase

The FastAPI backend integrates seamlessly with the existing AutoTrainX components:

### AutoTrainPipeline Integration
- Uses existing `src.pipeline.AutoTrainPipeline` for training operations
- Supports all three modes: single, batch, variations
- Maintains compatibility with existing configuration system

### Database Integration
- Uses existing `src.database.enhanced_manager.EnhancedDatabaseManager`
- Leverages existing job tracking and execution models
- Maintains data consistency with existing CLI operations

### Configuration Management
- Works with existing preset system in `Presets/` directory
- Uses existing dataset preparation workflows
- Integrates with existing workspace structure

## Development

### Project Structure
```
api/
├── __init__.py
├── main.py                 # FastAPI application
├── dependencies.py         # Dependency injection
├── exceptions.py          # Custom exceptions
├── requirements.txt       # API dependencies
├── models/
│   ├── __init__.py
│   └── schemas.py         # Pydantic models
├── routes/
│   ├── __init__.py
│   ├── jobs.py           # Job management
│   ├── training.py       # Training operations
│   ├── datasets.py       # Dataset management
│   └── presets.py        # Preset management
├── services/
│   ├── __init__.py
│   └── job_service.py    # Business logic
└── websockets/
    ├── __init__.py
    └── progress.py       # WebSocket handlers
api_server.py             # Server entry point
```

### Adding New Endpoints

1. **Define Pydantic Models** in `api/models/schemas.py`
2. **Add Business Logic** in appropriate service module
3. **Create Route Handler** in `api/routes/`
4. **Register Router** in `api/main.py`
5. **Update Dependencies** if needed

### Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests (when implemented)
pytest api/tests/
```

## Production Deployment

### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

EXPOSE 8000
CMD ["python", "api_server.py", "--prod", "--host", "0.0.0.0", "--workers", "4"]
```

### Nginx Configuration
```nginx
upstream autotrainx_api {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://autotrainx_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    location /ws/ {
        proxy_pass http://autotrainx_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Environment Variables
- `AUTOTRAINX_BASE_PATH`: Override base path
- `AUTOTRAINX_DB_PATH`: Override database path
- `AUTOTRAINX_LOG_LEVEL`: Set logging level
- `AUTOTRAINX_MAX_WORKERS`: Set maximum workers

## Security Considerations

### Authentication (To Be Implemented)
- JWT token-based authentication
- Role-based access control
- API key management

### Production Security
- Enable HTTPS with SSL certificates
- Configure CORS appropriately
- Implement rate limiting
- Add request validation and sanitization
- Monitor and log security events

## Monitoring and Observability

### Health Checks
- System health: `GET /health`
- Service-specific health checks on each router
- Database connectivity checks
- Pipeline readiness validation

### Logging
- Structured logging with timestamps
- Separate log files for API and services
- Configurable log levels
- Request/response logging

### Metrics (Future Enhancement)
- Prometheus metrics endpoint
- Job execution metrics
- API performance metrics
- WebSocket connection metrics

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure `src/` directory is in Python path
   - Check all dependencies are installed

2. **Database Connection Issues**
   - Verify `DB/` directory exists and is writable
   - Check database file permissions

3. **WebSocket Connection Failures**
   - Verify WebSocket support in client
   - Check firewall and proxy settings

4. **Job Execution Failures**
   - Check existing AutoTrainX configuration
   - Verify dataset and preset availability
   - Review job service logs

### Debug Mode
```bash
python api_server.py --dev --log-level debug
```

## Future Enhancements

- [ ] Authentication and authorization system
- [ ] Rate limiting and throttling
- [ ] Metrics and monitoring integration
- [ ] Batch job scheduling
- [ ] Multi-tenant support
- [ ] Advanced filtering and search
- [ ] Result visualization endpoints
- [ ] Model deployment integration
- [ ] Automated testing suite
- [ ] Performance optimization

## Contributing

1. Follow existing code structure and patterns
2. Add comprehensive error handling
3. Include Pydantic models for all endpoints
4. Add logging for debugging
5. Update documentation for new features
6. Consider backward compatibility with existing CLI

## License

This FastAPI backend follows the same license as the main AutoTrainX project.