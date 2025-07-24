"""
Database configuration and initialization for IPFS Storage System.

Handles SQLAlchemy setup, table creation, and database connections.
"""

import asyncio
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, Text, BigInteger, create_engine, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings

settings = get_settings()

# Create database engine
if settings.database_url.startswith("sqlite"):
    # For SQLite, use synchronous engine
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        echo=settings.debug
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    # For other databases, could use async engine
    engine = create_engine(settings.database_url, echo=settings.debug)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class FileRecord(Base):
    """Database model for storing file metadata."""
    
    __tablename__ = "files"
    
    id = Column(Integer, primary_key=True, index=True)
    cid = Column(String(255), unique=True, index=True, nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    content_type = Column(String(100))
    size = Column(BigInteger, nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    description = Column(Text)
    tags = Column(Text)  # JSON string of tags
    uploader_ip = Column(String(45))  # IPv4/IPv6 address
    is_pinned = Column(Integer, default=1)  # 1 for pinned, 0 for unpinned
    
    def __repr__(self):
        return f"<FileRecord(cid='{self.cid}', filename='{self.filename}')>"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "cid": self.cid,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "content_type": self.content_type,
            "size": self.size,
            "upload_date": self.upload_date.isoformat() if self.upload_date else None,
            "description": self.description,
            "tags": self.tags,
            "uploader_ip": self.uploader_ip,
            "is_pinned": bool(self.is_pinned)
        }


async def init_db():
    """Initialize the database and create tables."""
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully")
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
        raise


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class DatabaseService:
    """Service class for database operations."""
    
    def __init__(self):
        self.SessionLocal = SessionLocal
    
    def get_session(self):
        """Get a new database session."""
        return self.SessionLocal()
    
    def create_file_record(
        self,
        cid: str,
        filename: str,
        original_filename: str,
        content_type: Optional[str] = None,
        size: int = 0,
        description: Optional[str] = None,
        tags: Optional[str] = None,
        uploader_ip: Optional[str] = None
    ) -> FileRecord:
        """Create a new file record in the database."""
        db = self.get_session()
        try:
            file_record = FileRecord(
                cid=cid,
                filename=filename,
                original_filename=original_filename,
                content_type=content_type,
                size=size,
                description=description,
                tags=tags,
                uploader_ip=uploader_ip
            )
            db.add(file_record)
            db.commit()
            db.refresh(file_record)
            return file_record
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def get_file_by_cid(self, cid: str) -> Optional[FileRecord]:
        """Get file record by CID."""
        db = self.get_session()
        try:
            return db.query(FileRecord).filter(FileRecord.cid == cid).first()
        finally:
            db.close()
    
    def get_file_by_id(self, file_id: int) -> Optional[FileRecord]:
        """Get file record by ID."""
        db = self.get_session()
        try:
            return db.query(FileRecord).filter(FileRecord.id == file_id).first()
        finally:
            db.close()
    
    def get_all_files(self, skip: int = 0, limit: int = 100) -> list[FileRecord]:
        """Get all file records with pagination."""
        db = self.get_session()
        try:
            return db.query(FileRecord).offset(skip).limit(limit).all()
        finally:
            db.close()
    
    def list_files(self, skip: int = 0, limit: int = 50) -> tuple[list[FileRecord], int]:
        """List files with pagination, returning (files, total_count)."""
        db = self.get_session()
        try:
            total = db.query(FileRecord).count()
            files = db.query(FileRecord).offset(skip).limit(limit).all()
            return files, total
        finally:
            db.close()
    
    def search_files(self, query: str, skip: int = 0, limit: int = 100) -> tuple[list[FileRecord], int]:
        """Search files by filename or description, returning (files, total_count)."""
        db = self.get_session()
        try:
            base_query = db.query(FileRecord).filter(
                (FileRecord.filename.contains(query)) |
                (FileRecord.original_filename.contains(query)) |
                (FileRecord.description.contains(query))
            )
            total = base_query.count()
            files = base_query.offset(skip).limit(limit).all()
            return files, total
        finally:
            db.close()
    
    def update_file_record(self, cid: str, updates: dict) -> Optional[FileRecord]:
        """Update file record by CID."""
        db = self.get_session()
        try:
            file_record = db.query(FileRecord).filter(FileRecord.cid == cid).first()
            if file_record:
                for key, value in updates.items():
                    if hasattr(file_record, key):
                        setattr(file_record, key, value)
                db.commit()
                db.refresh(file_record)
                return file_record
            return None
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def delete_file_record(self, cid: str) -> bool:
        """Delete file record by CID."""
        db = self.get_session()
        try:
            file_record = db.query(FileRecord).filter(FileRecord.cid == cid).first()
            if file_record:
                db.delete(file_record)
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def get_file_count(self) -> int:
        """Get total number of files."""
        db = self.get_session()
        try:
            return db.query(FileRecord).count()
        finally:
            db.close()
    
    def get_total_size(self) -> int:
        """Get total size of all files."""
        db = self.get_session()
        try:
            result = db.query(func.sum(FileRecord.size)).scalar()
            return result or 0
        finally:
            db.close()
