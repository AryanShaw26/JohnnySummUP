"""
Central API v1 router binding all feature endpoints.
Supports both standard /medical/ namespaces and convenient aliases.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    analytics,
    auth,
    capabilities,
    dashboard,
    exports,
    insights,
    medical_documents,
    prescriptions,
    processing_jobs,
)

api_router = APIRouter()

# Authentication & Current User
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(auth.router, prefix="", tags=["Me"])

# Capabilities
api_router.include_router(capabilities.router, prefix="/medical", tags=["Capabilities"])

# Medical Documents & Records
api_router.include_router(medical_documents.router, prefix="/medical/documents", tags=["Medical Documents"])
api_router.include_router(medical_documents.router, prefix="/records", tags=["Records Alias"])

# Processing Jobs
api_router.include_router(processing_jobs.router, prefix="/medical/jobs", tags=["Processing Jobs"])

# Dashboard Overview
api_router.include_router(dashboard.router, prefix="/medical/dashboard", tags=["Dashboard"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard Alias"])

# Health Analytics & Trends
api_router.include_router(analytics.router, prefix="/medical/analytics", tags=["Analytics"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics Alias"])
api_router.include_router(analytics.router, prefix="/medical", tags=["Comparison"])

# Prescriptions
api_router.include_router(prescriptions.router, prefix="/medical/prescriptions", tags=["Prescriptions"])
api_router.include_router(prescriptions.router, prefix="/prescriptions", tags=["Prescriptions Alias"])

# AI Insights
api_router.include_router(insights.router, prefix="/medical/insights", tags=["AI Insights"])
api_router.include_router(insights.router, prefix="/insights", tags=["AI Insights Alias"])

# PDF Exports
api_router.include_router(exports.router, prefix="/medical/exports", tags=["Exports"])
api_router.include_router(exports.router, prefix="/exports", tags=["Exports Alias"])

