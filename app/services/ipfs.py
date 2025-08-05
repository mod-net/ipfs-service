"""
IPFS Service Integration for IPFS Storage System.

Handles all IPFS operations including file upload, retrieval, and node management.
"""

import asyncio
import io
from pathlib import Path
from typing import Any

import ipfshttpclient
from fastapi import HTTPException, UploadFile

from app.config import get_settings

settings = get_settings()


class IPFSService:
    """Service class for IPFS operations."""

    def __init__(self):
        self.api_url = settings.ipfs_api_url
        self.gateway_url = settings.ipfs_gateway_url
        self.timeout = settings.ipfs_timeout
        self._client = None

    def _get_client(self):
        """Get IPFS HTTP client with lazy initialization."""
        if self._client is None:
            try:
                # Convert HTTP URL to multiaddr format for ipfshttpclient
                # Parse URL and convert to multiaddr format
                from urllib.parse import urlparse

                parsed = urlparse(self.api_url)
                if parsed.scheme == 'http' and parsed.hostname:
                    # Convert hostname to IP for local development
                    hostname = parsed.hostname
                    if hostname == 'localhost':
                        hostname = '127.0.0.1'  # Standard loopback IP

                    port = parsed.port or 5001  # Default IPFS API port
                    addr = f"/ip4/{hostname}/tcp/{port}"
                else:
                    # Fallback to original URL for non-HTTP or malformed URLs
                    addr = self.api_url

                self._client = ipfshttpclient.connect(
                    addr=addr, timeout=self.timeout
                )
            except Exception as e:
                raise HTTPException(
                    status_code=503,
                    detail=f"Failed to connect to IPFS node at {self.api_url}: {str(e)}",
                ) from e
        return self._client

    async def get_node_info(self) -> dict[str, Any]:
        """Get IPFS node information with proper typing."""
        try:
            client = self._get_client()
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            node_info_raw = await loop.run_in_executor(None, client.id)
            # Ensure proper typing - IPFS client.id returns a dict
            node_info: dict[str, Any] = dict(node_info_raw) if node_info_raw else {}
            return node_info
        except Exception as e:
            msg = f"Failed to get IPFS node info: {str(e)}"
            raise HTTPException(status_code=503, detail=msg) from e

    async def add_file(self, file: UploadFile) -> dict[str, Any]:
        """
        Add a file to IPFS and return the CID and metadata.

        Args:
            file: FastAPI UploadFile object

        Returns:
            Dictionary containing CID, size, and other metadata
        """
        try:
            # Read file content
            content = await file.read()
            await file.seek(0)  # Reset file pointer

            # Validate file size
            if len(content) > settings.max_file_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size is {settings.max_file_size} bytes",
                )

            # Validate file extension
            if file.filename:
                file_ext = Path(file.filename).suffix.lower().lstrip(".")
                if file_ext and file_ext not in settings.allowed_extensions_list:
                    raise HTTPException(
                        status_code=415,
                        detail=(
                            f"File type '{file_ext}' not allowed. "
                            f"Allowed: {settings.allowed_extensions_list}"
                        ),
                    )

            client = self._get_client()

            # Add file to IPFS
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, lambda: client.add(io.BytesIO(content), pin=True)
            )

            # Extract CID from result
            cid = result["Hash"]

            return {
                "cid": cid,
                "size": len(content),
                "filename": file.filename or "unnamed",
                "content_type": file.content_type,
                "ipfs_result": result,
            }

        except HTTPException:
            raise
        except Exception as e:
            msg = f"Failed to add file to IPFS: {str(e)}"
            raise HTTPException(status_code=500, detail=msg) from e

    async def add_json_content(self, content: str, filename: str = "data.json") -> dict[str, Any]:
        """
        Add JSON content directly to IPFS without file type restrictions.

        Args:
            content: JSON string content to upload
            filename: Optional filename for the content

        Returns:
            Dictionary containing CID and upload information
        """
        try:
            content_bytes = content.encode('utf-8')
            client = self._get_client()

            # Add content to IPFS
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, lambda: client.add(io.BytesIO(content_bytes), pin=True)
            )

            # Extract CID from result
            cid = result["Hash"]

            return {
                "cid": cid,
                "size": len(content_bytes),
                "filename": filename,
                "content_type": "application/json",
                "ipfs_result": result,
            }

        except Exception as e:
            msg = f"Failed to add JSON content to IPFS: {str(e)}"
            raise HTTPException(status_code=500, detail=msg) from e

    async def get_file(self, cid: str) -> bytes:
        """
        Retrieve a file from IPFS by CID.

        Args:
            cid: Content identifier of the file

        Returns:
            File content as bytes
        """
        try:
            client = self._get_client()

            # Get file from IPFS
            loop = asyncio.get_event_loop()
            content_raw = await loop.run_in_executor(None, lambda: client.cat(cid))

            # Ensure proper typing - IPFS client.cat returns bytes
            content: bytes = bytes(content_raw) if content_raw else b""
            return content

        except Exception as e:
            raise HTTPException(
                status_code=404, detail=f"Failed to retrieve file from IPFS: {str(e)}"
            ) from e

    async def pin_file(self, cid: str) -> bool:
        """
        Pin a file in IPFS to prevent garbage collection.

        Args:
            cid: Content identifier of the file

        Returns:
            True if successful, False otherwise
        """
        try:
            client = self._get_client()

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: client.pin.add(cid))

            return True

        except Exception as e:
            print(f"Failed to pin file {cid}: {str(e)}")
            return False

    async def unpin_file(self, cid: str) -> bool:
        """
        Unpin a file in IPFS to allow garbage collection.

        Args:
            cid: Content identifier of the file

        Returns:
            True if successful, False otherwise
        """
        try:
            client = self._get_client()

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: client.pin.rm(cid))

            return True

        except Exception as e:
            print(f"Failed to unpin file {cid}: {str(e)}")
            return False

    async def get_file_stats(self, cid: str) -> dict[str, Any]:
        """
        Get statistics for a file in IPFS.

        Args:
            cid: Content identifier of the file

        Returns:
            Dictionary containing file statistics
        """
        try:
            client = self._get_client()

            loop = asyncio.get_event_loop()
            stats_raw = await loop.run_in_executor(
                None, lambda: client.object.stat(cid)
            )

            # Ensure proper typing - IPFS client.object.stat returns a dict
            stats: dict[str, Any] = dict(stats_raw) if stats_raw else {}
            return stats

        except Exception as e:
            msg = f"Failed to get file stats: {str(e)}"
            raise HTTPException(status_code=404, detail=msg) from e

    async def list_pinned_files(self) -> list[str]:
        """
        List all pinned files in IPFS.

        Returns:
            List of CIDs for pinned files
        """
        try:
            client = self._get_client()

            loop = asyncio.get_event_loop()
            pinned = await loop.run_in_executor(
                None, lambda: client.pin.ls(type="recursive")
            )

            return list(pinned.keys())

        except Exception as e:
            print(f"Failed to list pinned files: {str(e)}")
            return []

    async def check_connection(self) -> bool:
        """
        Check if IPFS node is accessible.

        Returns:
            True if connected, False otherwise
        """
        try:
            await self.get_node_info()
            return True
        except Exception:
            return False

    def get_gateway_url(self, cid: str) -> str:
        """
        Get the gateway URL for a file.

        Args:
            cid: Content identifier of the file

        Returns:
            Gateway URL for the file
        """
        return f"{self.gateway_url}/ipfs/{cid}"

    def close(self):
        """Close the IPFS client connection."""
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
