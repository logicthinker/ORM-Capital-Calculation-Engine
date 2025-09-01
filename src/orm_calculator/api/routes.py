"""
API routes for ORM Capital Calculator Engine
"""

from fastapi import APIRouter
from .loss_data_routes import router as loss_data_router
from .calculation_routes import router as calculation_router
from .lineage_routes import router as lineage_router
from .health_routes import router as health_router
from .consolidation_routes import router as consolidation_router
from .override_routes import router as override_router
from .analytics_routes import router as analytics_router
from .parameter_routes import router as parameter_router
from .performance_routes import router as performance_router

router = APIRouter()

# Include health check routes (public access)
router.include_router(health_router)

# Include calculation job routes
router.include_router(calculation_router)

# Include loss data management routes
router.include_router(loss_data_router)

# Include lineage and audit trail routes
router.include_router(lineage_router)

# Include consolidation and corporate actions routes
router.include_router(consolidation_router)

# Include supervisor override routes
router.include_router(override_router)

# Include analytics and stress testing routes
router.include_router(analytics_router)

# Include parameter management routes
router.include_router(parameter_router)

# Include performance monitoring routes
router.include_router(performance_router)