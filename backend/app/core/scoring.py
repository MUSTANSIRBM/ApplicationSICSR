import numpy as np
from typing import Dict, Any, Tuple, List
from datetime import datetime, date
from app.core.models import Defect, SafetyTier, ScoreResponse


class ScoringEngine:
    def __init__(self):
        # Weights for the scoring formula
        self.weights = {
            "severity": 0.4,
            "overdue": 0.35,
            "traffic_impact": 0.25
        }
        
        # Safety critical is handled as a tier gate, not a weight
        self.safety_tiers = {
            True: SafetyTier.SAFETY_CRITICAL,
            False: SafetyTier.HIGH  # Default tier for non-safety
        }
        
        # Tier-specific thresholds
        self.tier_thresholds = {
            SafetyTier.SAFETY_CRITICAL: float('inf'),
            SafetyTier.HIGH: 0.7,
            SafetyTier.MEDIUM: 0.4,
            SafetyTier.LOW: 0.0
        }
    
    def score_defect(self, defect: Defect, current_date: date) -> ScoreResponse:
        """Score a single defect with full explanation."""
        
        # Safety tier gate - this is a hard rule, not a weight
        if defect.safety_critical:
            tier = SafetyTier.SAFETY_CRITICAL
            # Safety-critical defects get a score of 100 (max possible)
            base_score = 100.0
        else:
            tier = self._determine_tier(defect)
            base_score = self._calculate_base_score(defect, current_date)
        
        # Build breakdown
        breakdown = self._get_breakdown(defect, current_date)
        
        # Create explanation
        explanation = self._generate_explanation(defect, tier, base_score, breakdown)
        
        return ScoreResponse(
            defect_id=defect.id,
            score=base_score,
            tier=tier,
            breakdown=breakdown,
            explanation=explanation
        )
    
    def _determine_tier(self, defect: Defect) -> SafetyTier:
        """Determine tier based on severity and other factors."""
        # This could be more sophisticated, but for now:
        if defect.severity >= 4:
            return SafetyTier.HIGH
        elif defect.severity >= 2:
            return SafetyTier.MEDIUM
        else:
            return SafetyTier.LOW
    
    def _calculate_base_score(self, defect: Defect, current_date: date) -> float:
        """Calculate score using weighted formula."""
        # Normalize severity (1-5) to 0-1
        norm_severity = (defect.severity - 1) / 4
        
        # Normalize overdue days with diminishing returns
        overdue_factor = min(defect.overdue_days / 30, 1.0)
        
        # Normalize traffic impact (1-5) to 0-1
        norm_traffic = (defect.traffic_impact - 1) / 4
        
        # Weighted sum
        score = (
            self.weights["severity"] * norm_severity +
            self.weights["overdue"] * overdue_factor +
            self.weights["traffic_impact"] * norm_traffic
        )
        
        # Scale to 0-100 for better UX
        return score * 100
    
    def _get_breakdown(self, defect: Defect, current_date: date) -> Dict[str, float]:
        """Get the score breakdown for explanation."""
        norm_severity = (defect.severity - 1) / 4
        overdue_factor = min(defect.overdue_days / 30, 1.0)
        norm_traffic = (defect.traffic_impact - 1) / 4
        
        return {
            "severity_score": norm_severity * 100 * self.weights["severity"],
            "overdue_score": overdue_factor * 100 * self.weights["overdue"],
            "traffic_score": norm_traffic * 100 * self.weights["traffic_impact"],
            "safety_bonus": 100.0 if defect.safety_critical else 0.0
        }
    
    def _generate_explanation(self, defect: Defect, tier: SafetyTier, 
                             score: float, breakdown: Dict[str, float]) -> str:
        """Generate a human-readable explanation of the score."""
        parts = []
        
        if defect.safety_critical:
            parts.append("⚠️ SAFETY CRITICAL: This defect is flagged as safety-critical and must be prioritized above all others.")
        else:
            parts.append(f"📊 Score calculated from:")
            parts.append(f"  - Severity: {defect.severity}/5 → {breakdown['severity_score']:.1f} points")
            parts.append(f"  - Overdue days: {defect.overdue_days} → {breakdown['overdue_score']:.1f} points")
            parts.append(f"  - Traffic impact: {defect.traffic_impact}/5 → {breakdown['traffic_score']:.1f} points")
        
        parts.append(f"\n📈 Final score: {score:.1f}/100")
        parts.append(f"🏷️ Tier: {tier.value}")
        
        return "\n".join(parts)
    
    def score_defects(self, defects: List[Defect], current_date: date) -> List[ScoreResponse]:
        """Score multiple defects and sort them."""
        scored = [self.score_defect(d, current_date) for d in defects]
        
        # Sort by tier (safety first) then by score
        tier_order = {
            SafetyTier.SAFETY_CRITICAL: 0,
            SafetyTier.HIGH: 1,
            SafetyTier.MEDIUM: 2,
            SafetyTier.LOW: 3
        }
        
        return sorted(scored, key=lambda x: (tier_order[x.tier], -x.score))


# Offline ML validation - not used in live scoring
class MLWeightValidator:
    def __init__(self):
        self.model = None
        
    def validate_weights(self, synthetic_data):
        """Use scikit-learn/XGBoost offline to validate weights."""
        # This would be used during development, not in production
        pass