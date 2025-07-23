# IPFS-Based Storage System

## Project Overview

A distributed file storage system built on IPFS (InterPlanetary File System) that provides a RESTful API and web interface for file management. The system leverages IPFS's content-addressed storage to ensure data integrity and availability across a distributed network.

## Core Features

### API Layer
- **File Upload**: Store files to IPFS and return content hash (CID)
- **File Retrieval**: Fetch files by CID or metadata
- **File Metadata**: Store and query file metadata (name, size, type, upload date)
- **File Listing**: Browse available files with pagination
- **File Deletion**: Remove files from local node (IPFS content remains distributed)

### Web UI
- **File Browser**: Visual interface to browse stored files
- **Upload Interface**: Drag-and-drop file upload with progress indicators
- **File Preview**: Preview common file types (images, text, PDFs)
- **Search & Filter**: Search files by name, type, or metadata
- **File Management**: Download, share, and organize files

## Technical Specifications

### Backend Stack
- **Framework**: FastAPI for high-performance async API
- **Data Models**: Pydantic v2 for request/response validation
- **IPFS Integration**: py-ipfs-http-client for IPFS node communication
- **Database**: SQLite for metadata storage (upgradeable to PostgreSQL)
- **Authentication**: JWT-based authentication (optional)

### Frontend Stack
- **Framework**: Modern HTML5/CSS3/JavaScript (or React/Vue if needed)
- **Styling**: Tailwind CSS or similar utility-first framework
- **File Handling**: Modern File API with drag-and-drop support

### IPFS Requirements
- Local IPFS node or connection to remote IPFS gateway
- Support for IPFS HTTP API
- Content addressing and retrieval
- Optional: IPFS pinning for data persistence

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web UI        │    │   FastAPI       │    │   IPFS Node     │
│   (Frontend)    │◄──►│   Backend       │◄──►│   (Storage)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   SQLite DB     │
                       │   (Metadata)    │
                       └─────────────────┘
```

## API Endpoints

- `POST /files/upload` - Upload file to IPFS
- `GET /files/{cid}` - Retrieve file by CID
- `GET /files/` - List files with metadata
- `DELETE /files/{cid}` - Remove file from local storage
- `GET /files/{cid}/info` - Get file metadata
- `POST /files/search` - Search files by criteria

## Success Criteria

1. Successfully store and retrieve files via IPFS
2. Functional web interface for file management
3. RESTful API with proper error handling
4. File metadata persistence and querying
5. Basic security measures implemented
6. Documentation for setup and usage

## Future Enhancements

- File sharing with access controls
- File versioning and history
- Bulk operations (upload/download multiple files)
- Integration with IPFS clusters
- Mobile-responsive design
- File encryption before IPFS storage
