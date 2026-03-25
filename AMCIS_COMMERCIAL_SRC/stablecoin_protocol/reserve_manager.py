#!/usr/bin/env python3
"""
AMCIS™ Reserve Manager
======================
Manages multi-asset reserves backing the stablecoin.

Features:
- Multi-asset collateral management
- Rebalancing strategies
- Risk diversification
- Liquidity optimization

Commercial Version - Requires License
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum
import logging

logger = logging.getLogger("ReserveManager")


class AssetType(Enum):
    """Types of reserve assets."""
    FIAT = "fiat"
    CRYPTO = "crypto"
    COMMODITY = "commodity"
    BOND = "bond"
    OTHER = "other"


@dataclass
class ReserveAsset:
    """A single reserve asset."""
    asset_id: str
    name: str
    asset_type: AssetType
    symbol: str
    quantity: float
    unit_value: float
    target_allocation: float  # Target percentage (0-1)
    
    @property
    def total_value(self) -> float:
        """Calculate total value of holding."""
        return self.quantity * self.unit_value


class ReserveManager:
    """
    Multi-Asset Reserve Manager
    
    Manages the basket of assets backing the stablecoin.
    Ensures sufficient collateral and optimal allocation.
    
    Args:
        min_collateral_ratio: Minimum required collateral (default 1.2)
        target_collateral_ratio: Target collateral level (default 1.5)
    """
    
    def __init__(
        self,
        min_collateral_ratio: float = 1.2,
        target_collateral_ratio: float = 1.5
    ):
        self.min_collateral_ratio = min_collateral_ratio
        self.target_collateral_ratio = target_collateral_ratio
        
        self.assets: Dict[str, ReserveAsset] = {}
        self.stablecoin_supply: float = 0.0
        
        logger.info(f"Reserve Manager initialized (min_ratio={min_collateral_ratio})")
    
    def add_asset(self, asset: ReserveAsset) -> None:
        """Add a reserve asset."""
        self.assets[asset.asset_id] = asset
        logger.info(f"Added reserve asset: {asset.name} ({asset.symbol})")
    
    def update_price(self, asset_id: str, new_price: float) -> None:
        """Update the price of an asset."""
        if asset_id in self.assets:
            old_value = self.assets[asset_id].total_value
            self.assets[asset_id].unit_value = new_price
            new_value = self.assets[asset_id].total_value
            
            logger.info(f"Price update: {asset_id} ${new_price:.2f} "
                       f"(value change: ${new_value - old_value:,.2f})")
    
    def get_total_reserve_value(self) -> float:
        """Calculate total value of all reserves."""
        return sum(asset.total_value for asset in self.assets.values())
    
    def get_collateral_ratio(self) -> float:
        """Calculate current collateral ratio."""
        if self.stablecoin_supply == 0:
            return float('inf')
        return self.get_total_reserve_value() / self.stablecoin_supply
    
    def is_sufficiently_collateralized(self) -> bool:
        """Check if reserves meet minimum collateral ratio."""
        return self.get_collateral_ratio() >= self.min_collateral_ratio
    
    def get_allocation(self) -> Dict[str, float]:
        """Get current allocation percentages."""
        total = self.get_total_reserve_value()
        if total == 0:
            return {}
        
        return {
            asset_id: asset.total_value / total
            for asset_id, asset in self.assets.items()
        }
    
    def get_rebalancing_recommendations(self) -> List[dict]:
        """Get recommendations for rebalancing portfolio."""
        recommendations = []
        current_allocation = self.get_allocation()
        
        for asset_id, asset in self.assets.items():
            current = current_allocation.get(asset_id, 0)
            target = asset.target_allocation
            diff = current - target
            
            if abs(diff) > 0.05:  # 5% threshold
                action = "reduce" if diff > 0 else "increase"
                recommendations.append({
                    "asset_id": asset_id,
                    "asset_name": asset.name,
                    "current_allocation": current,
                    "target_allocation": target,
                    "difference": diff,
                    "action": action,
                    "priority": "high" if abs(diff) > 0.1 else "medium"
                })
        
        return recommendations
    
    def mint_stablecoin(self, amount: float) -> bool:
        """
        Mint new stablecoins (increases supply).
        
        Args:
            amount: Amount to mint
            
        Returns:
            True if minting is allowed
        """
        # Simulate new supply
        new_supply = self.stablecoin_supply + amount
        new_ratio = self.get_total_reserve_value() / new_supply
        
        if new_ratio < self.min_collateral_ratio:
            logger.warning(f"Minting rejected: would reduce collateral ratio to {new_ratio:.2f}")
            return False
        
        self.stablecoin_supply = new_supply
        logger.info(f"Minted {amount:,.2f} stablecoins. New supply: {self.stablecoin_supply:,.2f}")
        return True
    
    def burn_stablecoin(self, amount: float) -> None:
        """Burn stablecoins (decreases supply)."""
        self.stablecoin_supply = max(0, self.stablecoin_supply - amount)
        logger.info(f"Burned {amount:,.2f} stablecoins. New supply: {self.stablecoin_supply:,.2f}")
    
    def get_status(self) -> dict:
        """Get comprehensive reserve status."""
        return {
            "total_reserve_value": self.get_total_reserve_value(),
            "stablecoin_supply": self.stablecoin_supply,
            "collateral_ratio": self.get_collateral_ratio(),
            "min_required_ratio": self.min_collateral_ratio,
            "target_ratio": self.target_collateral_ratio,
            "is_sufficiently_collateralized": self.is_sufficiently_collateralized(),
            "allocation": self.get_allocation(),
            "rebalancing_needed": len(self.get_rebalancing_recommendations()) > 0
        }
