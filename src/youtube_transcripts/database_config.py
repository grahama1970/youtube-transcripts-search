"""
Database Configuration for YouTube Transcripts
Supports both SQLite (standalone) and ArangoDB (Granger integration)

This module provides configuration for dual database support,
allowing the project to work standalone or as part of Granger.

External Dependencies:
- python-dotenv: For environment variable loading
- pydantic: For configuration validation

Example Usage:
>>> from youtube_transcripts.database_config import get_database_config
>>> config = get_database_config()
>>> print(config.backend)  # 'sqlite' or 'arangodb'
"""

import os
from typing import Optional, Literal, Dict, Any
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class SQLiteConfig:
    """Configuration for SQLite backend"""
    db_path: str = "youtube_transcripts.db"
    
    # Performance settings
    journal_mode: str = "WAL"  # Write-Ahead Logging for better concurrency
    cache_size: int = -64000  # 64MB cache
    synchronous: str = "NORMAL"  # Balance between safety and speed
    
    # FTS5 settings
    fts_tokenize: str = "porter"  # Porter stemming for better search
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'db_path': self.db_path,
            'journal_mode': self.journal_mode,
            'cache_size': self.cache_size,
            'synchronous': self.synchronous,
            'fts_tokenize': self.fts_tokenize
        }


@dataclass
class ArangoDBConfig:
    """Configuration for ArangoDB backend"""
    host: str = "http://localhost:8529"
    database: str = "memory_bank"  # Granger's unified memory bank
    username: str = "root"
    password: str = ""
    
    # Collection prefix for YouTube data
    collection_prefix: str = "youtube_"
    
    # Graph name
    graph_name: str = "youtube_knowledge_graph"
    
    # Connection pool settings
    connection_pool_size: int = 10
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'host': self.host,
            'database': self.database,
            'username': self.username,
            'password': self.password,
            'collection_prefix': self.collection_prefix,
            'graph_name': self.graph_name
        }


@dataclass
class DatabaseConfig:
    """Main database configuration"""
    
    # Backend selection
    backend: Literal["sqlite", "arangodb", "auto"] = "auto"
    
    # Backend-specific configs
    sqlite: SQLiteConfig = None
    arangodb: ArangoDBConfig = None
    
    # Feature flags
    enable_embeddings: bool = True
    enable_graph_features: bool = True
    enable_research_features: bool = True
    
    # Cache settings (applies to both backends)
    cache_enabled: bool = True
    cache_ttl: int = 3600  # 1 hour
    
    def __post_init__(self):
        if self.sqlite is None:
            self.sqlite = SQLiteConfig()
        if self.arangodb is None:
            self.arangodb = ArangoDBConfig()
    
    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create configuration from environment variables"""
        # Determine backend
        backend = os.getenv("YOUTUBE_DB_BACKEND", "auto")
        
        # SQLite configuration
        sqlite_config = SQLiteConfig(
            db_path=os.getenv("YOUTUBE_SQLITE_PATH", "youtube_transcripts.db"),
            journal_mode=os.getenv("YOUTUBE_SQLITE_JOURNAL_MODE", "WAL"),
            cache_size=int(os.getenv("YOUTUBE_SQLITE_CACHE_SIZE", "-64000")),
            synchronous=os.getenv("YOUTUBE_SQLITE_SYNCHRONOUS", "NORMAL")
        )
        
        # ArangoDB configuration
        arangodb_config = ArangoDBConfig(
            host=os.getenv("YOUTUBE_ARANGO_HOST", "http://localhost:8529"),
            database=os.getenv("YOUTUBE_ARANGO_DATABASE", "memory_bank"),
            username=os.getenv("YOUTUBE_ARANGO_USERNAME", "root"),
            password=os.getenv("YOUTUBE_ARANGO_PASSWORD", ""),
            collection_prefix=os.getenv("YOUTUBE_ARANGO_PREFIX", "youtube_"),
            graph_name=os.getenv("YOUTUBE_ARANGO_GRAPH", "youtube_knowledge_graph")
        )
        
        return cls(
            backend=backend,
            sqlite=sqlite_config,
            arangodb=arangodb_config,
            enable_embeddings=os.getenv("YOUTUBE_ENABLE_EMBEDDINGS", "true").lower() == "true",
            enable_graph_features=os.getenv("YOUTUBE_ENABLE_GRAPH", "true").lower() == "true",
            enable_research_features=os.getenv("YOUTUBE_ENABLE_RESEARCH", "true").lower() == "true",
            cache_enabled=os.getenv("YOUTUBE_CACHE_ENABLED", "true").lower() == "true",
            cache_ttl=int(os.getenv("YOUTUBE_CACHE_TTL", "3600"))
        )
    
    def get_backend_config(self) -> Dict[str, Any]:
        """Get configuration for the selected backend"""
        if self.backend == "sqlite":
            return {
                'backend': 'sqlite',
                'sqlite_path': self.sqlite.db_path,
                **self.sqlite.to_dict()
            }
        elif self.backend == "arangodb":
            return {
                'backend': 'arangodb',
                'arango_config': self.arangodb.to_dict()
            }
        else:  # auto
            return {
                'backend': 'auto',
                'sqlite_path': self.sqlite.db_path,
                'arango_config': self.arangodb.to_dict()
            }
    
    def requires_arangodb(self) -> bool:
        """Check if configuration requires ArangoDB features"""
        return (
            self.backend == "arangodb" or
            (self.backend == "auto" and (
                self.enable_graph_features or
                self.enable_embeddings
            ))
        )


# Global configuration instance
_config: Optional[DatabaseConfig] = None


def get_database_config() -> DatabaseConfig:
    """Get or create database configuration"""
    global _config
    if _config is None:
        _config = DatabaseConfig.from_env()
    return _config


def set_database_config(config: DatabaseConfig):
    """Set database configuration (useful for testing)"""
    global _config
    _config = config


def create_database_adapter():
    """Create a database adapter based on current configuration"""
    from .database_adapter import DatabaseAdapter
    
    config = get_database_config()
    return DatabaseAdapter(config.get_backend_config())


# Environment variable template
ENV_TEMPLATE = """
# YouTube Transcripts Database Configuration

# Backend selection: sqlite, arangodb, or auto (auto-detect)
YOUTUBE_DB_BACKEND=auto

# SQLite Configuration (for standalone usage)
YOUTUBE_SQLITE_PATH=youtube_transcripts.db
YOUTUBE_SQLITE_JOURNAL_MODE=WAL
YOUTUBE_SQLITE_CACHE_SIZE=-64000
YOUTUBE_SQLITE_SYNCHRONOUS=NORMAL

# ArangoDB Configuration (for Granger integration)
YOUTUBE_ARANGO_HOST=http://localhost:8529
YOUTUBE_ARANGO_DATABASE=memory_bank
YOUTUBE_ARANGO_USERNAME=root
YOUTUBE_ARANGO_PASSWORD=
YOUTUBE_ARANGO_PREFIX=youtube_
YOUTUBE_ARANGO_GRAPH=youtube_knowledge_graph

# Feature Flags
YOUTUBE_ENABLE_EMBEDDINGS=true
YOUTUBE_ENABLE_GRAPH=true
YOUTUBE_ENABLE_RESEARCH=true

# Cache Settings
YOUTUBE_CACHE_ENABLED=true
YOUTUBE_CACHE_TTL=3600
"""


def create_env_template(path: str = ".env.example"):
    """Create an example environment file"""
    with open(path, 'w') as f:
        f.write(ENV_TEMPLATE)
    print(f"Created {path}")


if __name__ == "__main__":
    # Example usage
    config = get_database_config()
    print(f"Backend: {config.backend}")
    print(f"SQLite path: {config.sqlite.db_path}")
    print(f"ArangoDB host: {config.arangodb.host}")
    print(f"Requires ArangoDB: {config.requires_arangodb()}")
    
    # Create example env file
    create_env_template()