"""
AMCIS Q-SEC CORE Commercial Module
===================================

Commercial licensing, watermarking, and distribution tools.

Copyright (c) 2026 AMCIS Security Corporation
All rights reserved.
"""

from .licensing import (
    LicenseManager, LicenseTier, LicenseStatus, LicenseMetadata,
    HardwareFingerprint, get_license_manager, require_license
)
from .watermark import (
    SourceCodeWatermarker, apply_customer_watermark, verify_watermark
)
from .package_builder import SecurePackageBuilder

__all__ = [
    'LicenseManager', 'LicenseTier', 'LicenseStatus', 'LicenseMetadata',
    'HardwareFingerprint', 'get_license_manager', 'require_license',
    'SourceCodeWatermarker', 'apply_customer_watermark', 'verify_watermark',
    'SecurePackageBuilder'
]

__version__ = '1.0.0-commercial'
