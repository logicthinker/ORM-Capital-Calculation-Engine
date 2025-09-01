"""
Database layer for ORM Capital Calculator Engine
"""

from .connection import (
    DatabaseConfig,
    DatabaseManager,
    db_manager,
    get_db_session,
    init_database,
    close_database,
)

from .repositories import (
    BaseRepository,
    BusinessIndicatorRepository,
    LossEventRepository,
    RecoveryRepository,
    CapitalCalculationRepository,
    JobRepository,
    AuditTrailRepository,
    RepositoryFactory,
)

__all__ = [
    # Database Connection
    "DatabaseConfig",
    "DatabaseManager",
    "db_manager",
    "get_db_session",
    "init_database",
    "close_database",
    # Repositories
    "BaseRepository",
    "BusinessIndicatorRepository",
    "LossEventRepository",
    "RecoveryRepository",
    "CapitalCalculationRepository",
    "JobRepository",
    "AuditTrailRepository",
    "RepositoryFactory",
]