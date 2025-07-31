"""
Database configuration and initialization for IPFS Storage System.

Handles SQLAlchemy setup, table creation, and database connections.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
    func,
    select,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session, Mapped, mapped_column
from typing import Optional, List, Type
from datetime import datetime

from app.config import get_settings

settings = get_settings()

# Create database engine
if settings.database_url.startswith("sqlite"):
    # For SQLite, use synchronous engine
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        echo=settings.debug,
    )
else:
    # For other databases, could use async engine
    engine = create_engine(settings.database_url, echo=settings.debug)

# Create session factory with proper SQLAlchemy 2.0 typing
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 style declarative base class."""
    pass


class FileRecord(Base):
    """Database model for storing file metadata with SQLAlchemy 2.0 typing."""

    __tablename__ = "files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cid: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    filename: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[Optional[str]] = mapped_column(String(100))
    size: Mapped[int] = mapped_column(BigInteger)
    upload_date: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    description: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[str]] = mapped_column(Text)  # JSON string of tags
    uploader_ip: Mapped[Optional[str]] = mapped_column(String(45))  # IPv4/IPv6 address
    is_pinned: Mapped[int] = mapped_column(Integer, default=1)  # 1 for pinned, 0 for unpinned

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
            "is_pinned": bool(self.is_pinned),
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

    def get_session(self) -> Session:
        """Get a new database session."""
        session: Session = self.SessionLocal()
        return session

    def create_file_record(
        self,
        cid: str,
        filename: str,
        original_filename: str,
        content_type: str | None = None,
        size: int = 0,
        description: str | None = None,
        tags: str | None = None,
        uploader_ip: str | None = None,
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
                uploader_ip=uploader_ip,
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
        """Get file record by CID using SQLAlchemy 2.0 style."""
        db = self.get_session()
        try:
            stmt = select(FileRecord).where(FileRecord.cid == cid)
            result = db.execute(stmt)
            return result.scalar_one_or_none()
        finally:
            db.close()

    def get_file_by_id(self, file_id: int) -> Optional[FileRecord]:
        """Get file record by ID using SQLAlchemy 2.0 style."""
        db = self.get_session()
        try:
            stmt = select(FileRecord).where(FileRecord.id == file_id)
            result = db.execute(stmt)
            return result.scalar_one_or_none()
        finally:
            db.close()

    def get_all_files(self, skip: int = 0, limit: int = 100) -> List[FileRecord]:
        """Get all file records with pagination using SQLAlchemy 2.0 style."""
        db = self.get_session()
        try:
            stmt = select(FileRecord).offset(skip).limit(limit)
            result = db.execute(stmt)
            return list(result.scalars().all())
        finally:
            db.close()

    def list_files(
        self, skip: int = 0, limit: int = 50
    ) -> tuple[List[FileRecord], int]:
        """List files with pagination using SQLAlchemy 2.0 style, returning (files, total_count)."""
        db = self.get_session()
        try:
            # Get total count
            count_stmt = select(func.count(FileRecord.id))
            total_result = db.execute(count_stmt)
            total = total_result.scalar() or 0
            
            # Get paginated files
            files_stmt = select(FileRecord).offset(skip).limit(limit)
            files_result = db.execute(files_stmt)
            files = list(files_result.scalars().all())
            
            return files, total
        finally:
            db.close()

    def search_files(
        self, query: str, skip: int = 0, limit: int = 100
    ) -> tuple[List[FileRecord], int]:
        """Search files by filename or description using SQLAlchemy 2.0 style, returning (files, total_count)."""
        db = self.get_session()
        try:
            # Build search condition
            search_condition = (
                (FileRecord.filename.contains(query))
                | (FileRecord.original_filename.contains(query))
                | (FileRecord.description.contains(query))
            )
            
            # Get total count
            count_stmt = select(func.count(FileRecord.id)).where(search_condition)
            total_result = db.execute(count_stmt)
            total = total_result.scalar() or 0
            
            # Get paginated results
            files_stmt = select(FileRecord).where(search_condition).offset(skip).limit(limit)
            files_result = db.execute(files_stmt)
            files = list(files_result.scalars().all())
            
            return files, total
        finally:
            db.close()

    def update_file_record(self, cid: str, updates: dict) -> Optional[FileRecord]:
        """Update file record by CID using SQLAlchemy 2.0 style."""
        db = self.get_session()
        try:
            # Get the record first
            stmt = select(FileRecord).where(FileRecord.cid == cid)
            result = db.execute(stmt)
            file_record = result.scalar_one_or_none()
            
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
        """Delete file record by CID using SQLAlchemy 2.0 style."""
        db = self.get_session()
        try:
            # Get the record first
            stmt = select(FileRecord).where(FileRecord.cid == cid)
            result = db.execute(stmt)
            file_record = result.scalar_one_or_none()
            
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
        """Get total number of files using SQLAlchemy 2.0 style."""
        db = self.get_session()
        try:
            stmt = select(func.count(FileRecord.id))
            result = db.execute(stmt)
            return result.scalar() or 0
        finally:
            db.close()

    def get_total_size(self) -> int:
        """Get total size of all files using SQLAlchemy 2.0 style."""
        db = self.get_session()
        try:
            stmt = select(func.sum(FileRecord.size))
            result = db.execute(stmt)
            return result.scalar() or 0
        finally:
            db.close()
