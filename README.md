# IPFS Storage System

A distributed file storage system built on IPFS (InterPlanetary File System) with a FastAPI backend and web interface for seamless file management.

## Features

- 🚀 **FastAPI Backend**: High-performance async API with automatic documentation
- 📁 **IPFS Integration**: Distributed file storage with content addressing
- 🌐 **Web Interface**: Modern UI for file upload, browsing, and management
- 🔍 **Search & Filter**: Find files by name, type, or metadata
- 📊 **Metadata Storage**: SQLite database for file information and indexing
- 🔒 **Security Ready**: JWT authentication support (optional)

## Quick Start

### Prerequisites

- Python 3.8+
- IPFS node (local or remote)
- uv package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ipfs
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Set up IPFS**
   
   **Option A: Local IPFS Node**
   ```bash
   # Install IPFS (if not already installed)
   wget https://dist.ipfs.io/go-ipfs/v0.14.0/go-ipfs_v0.14.0_linux-amd64.tar.gz
   tar -xvzf go-ipfs_v0.14.0_linux-amd64.tar.gz
   sudo mv go-ipfs/ipfs /usr/local/bin/
   
   # Initialize and start IPFS
   ipfs init
   ipfs daemon
   ```
   
   **Option B: Use Public Gateway** (for development only)
   ```bash
   # Configure in environment variables
   export IPFS_API_URL="https://ipfs.infura.io:5001"
   ```

4. **Run the application**
   ```bash
   uv run main.py
   ```

5. **Access the application**
   - API Documentation: http://localhost:8000/docs
   - Web Interface: http://localhost:8000

## Project Structure

```
ipfs/
├── main.py              # FastAPI application entry point
├── app/
│   ├── __init__.py
│   ├── api/             # API route handlers
│   │   ├── __init__.py
│   │   └── files.py     # File management endpoints
│   ├── models/          # Pydantic data models
│   │   ├── __init__.py
│   │   └── file.py      # File-related models
│   ├── services/        # Business logic
│   │   ├── __init__.py
│   │   ├── ipfs.py      # IPFS integration
│   │   └── database.py  # Database operations
│   └── static/          # Web UI assets
│       ├── index.html
│       ├── style.css
│       └── script.js
├── tests/               # Test suite
├── pyproject.toml       # Project configuration
└── README.md           # This file
```

## API Endpoints

### File Operations

- `POST /api/files/upload` - Upload file to IPFS
- `GET /api/files/{cid}` - Download file by CID
- `GET /api/files/` - List all files with metadata
- `DELETE /api/files/{cid}` - Remove file from local storage
- `GET /api/files/{cid}/info` - Get file metadata
- `POST /api/files/search` - Search files by criteria

### Example Usage

```bash
# Upload a file
curl -X POST "http://localhost:8000/api/files/upload" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@example.txt"

# Get file info
curl "http://localhost:8000/api/files/{cid}/info"

# Download file
curl "http://localhost:8000/api/files/{cid}" -o downloaded_file.txt
```

## Configuration

Environment variables:

```bash
# IPFS Configuration
IPFS_API_URL=http://localhost:5001  # IPFS API endpoint
IPFS_GATEWAY_URL=http://localhost:8080  # IPFS gateway for file access

# Database
DATABASE_URL=sqlite:///./files.db  # SQLite database path

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Security (optional)
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Development

### Running Tests

```bash
uv run pytest
```

### Code Formatting

```bash
uv run black .
uv run isort .
```

### Type Checking

```bash
uv run mypy .
```

## Deployment

### Docker (Recommended)

```dockerfile
# Dockerfile example
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install uv
RUN uv sync

EXPOSE 8000
CMD ["uv", "run", "main.py"]
```

### Production Considerations

- Use PostgreSQL instead of SQLite for better performance
- Set up IPFS cluster for redundancy
- Configure reverse proxy (nginx) for static file serving
- Enable HTTPS with SSL certificates
- Set up monitoring and logging

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Troubleshooting

### Common Issues

**IPFS Connection Failed**
- Ensure IPFS daemon is running: `ipfs daemon`
- Check IPFS API URL in configuration
- Verify firewall settings for port 5001

**File Upload Errors**
- Check file size limits in FastAPI configuration
- Ensure sufficient disk space
- Verify IPFS node has write permissions

**Database Errors**
- Check SQLite file permissions
- Ensure database directory exists
- Run database migrations if applicable

## Support

For support and questions:
- Create an issue on GitHub
- Check the [IPFS documentation](https://docs.ipfs.io/)
- Review [FastAPI documentation](https://fastapi.tiangolo.com/)