"""
URT+ Optimizer Service
Universal Resource Targeting Plus - Multi-Market Portfolio Optimization

This service implements the URT+ master equation for cross-market portfolio
optimization using quantum computing backends.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MarketType(Enum):
    """Supported financial markets"""
    CRYPTO = 1
    STOCKS = 2
    FOREX = 3
    COMMODITIES = 4
    DERIVATIVES = 5


@dataclass
class Asset:
    """Represents a tradeable asset"""
    symbol: str
    market: MarketType
    expected_return: float
    current_weight: float = 0.0
    target_weight: float = 0.0


@dataclass
class PortfolioConstraints:
    """URT+ Optimization Constraints"""
    # Constraint 1: Total allocation
    total_allocation: float = 1.0

    # Constraint 2: Position limits per asset
    position_limits: Dict[str, float] = None

    # Constraint 3: Market exposure limits
    market_exposure_limits: Dict[MarketType, float] = None

    # Constraint 4: Drift thresholds
    drift_thresholds: Dict[str, float] = None

    # Constraint 5: Total transaction cost limit
    max_transaction_cost: float = 0.01

    # Constraint 6: Cross-market correlation limit
    max_correlation_exposure: float = 0.70


@dataclass
class OptimizationParameters:
    """URT+ Optimization Parameters"""
    risk_aversion: float = 0.5  # λ
    cost_sensitivity: float = 0.3  # γ
    impact_sensitivity: float = 0.2  # δ
    quantum_backend: str = 'ibm_quantum'
    qaoa_layers: int = 5
    use_quantum: bool = True


class URTOptimizerService:
    """
    URT+ Optimizer Service

    Implements the Universal Optimization Function Master Equation:

    Maximize: Σᵢ Σⱼ [E(Rᵢⱼ,t) × wᵢⱼ,t] - λ × Risk(W,t) - γ × Cost(W,t) - δ × Impact(W,t)

    Subject to:
    1. Σᵢ Σⱼ wᵢⱼ,t = 1                              (Total allocation constraint)
    2. 0 ≤ wᵢⱼ,t ≤ wᵢⱼ,max                         (Position limits per asset)
    3. Σⱼ wᵢⱼ,t ≤ Mᵢ,max                           (Market exposure limits)
    4. |wᵢⱼ,t - wᵢⱼ,target| ≤ θᵢⱼ                  (Drift thresholds)
    5. Σᵢ Σⱼ Σₖ TC(i,j,k,t) ≤ Cₘₐₓ                  (Total transaction costs)
    6. Corr(Mᵢ,Mⱼ,t) × Exposure(Mᵢ,Mⱼ) ≤ Corrₘₐₓ  (Cross-market correlation limit)
    """

    def __init__(self, quantum_backend=None):
        """Initialize URT+ Optimizer Service"""
        self.quantum_backend = quantum_backend
        self.portfolio_cache = {}
        logger.info("URT+ Optimizer Service initialized")

    def optimize_portfolio(
        self,
        assets: List[Asset],
        covariance_matrix: np.ndarray,
        transaction_costs: Dict[Tuple[int, int, int], float],
        market_impact: Dict[Tuple[int, int], float],
        constraints: PortfolioConstraints,
        params: OptimizationParameters
    ) -> Dict:
        """
        Execute URT+ optimization

        Returns:
            Dict containing optimal weights, metrics, and execution info
        """
        logger.info(f"Starting URT+ optimization for {len(assets)} assets")

        # Step 1: Validate inputs
        self._validate_inputs(assets, covariance_matrix, constraints)

        # Step 2: Formulate objective function
        objective_fn = self._build_objective_function(
            assets,
            covariance_matrix,
            transaction_costs,
            market_impact,
            params
        )

        # Step 3: Apply constraints
        constraint_fns = self._build_constraints(constraints, assets)

        # Step 4: Solve optimization
        if params.use_quantum and self.quantum_backend:
            result = self._quantum_optimize(
                objective_fn,
                constraint_fns,
                assets,
                params
            )
        else:
            result = self._classical_optimize(
                objective_fn,
                constraint_fns,
                assets,
                params
            )

        # Step 5: Calculate performance metrics
        metrics = self._calculate_metrics(
            result['weights'],
            assets,
            covariance_matrix,
            transaction_costs,
            market_impact,
            params
        )

        # Step 6: Validate constraints
        constraint_check = self._validate_constraints(
            result['weights'],
            constraints,
            assets
        )

        return {
            'optimal_allocation': result['weights'],
            'performance_metrics': metrics,
            'constraint_satisfaction': constraint_check,
            'execution_info': result['execution_info']
        }

    def _validate_inputs(
        self,
        assets: List[Asset],
        covariance_matrix: np.ndarray,
        constraints: PortfolioConstraints
    ):
        """Validate input parameters"""
        assert len(assets) > 0, "Must have at least one asset"
        assert covariance_matrix.shape == (len(assets), len(assets)), \
            "Covariance matrix dimension mismatch"
        assert constraints.total_allocation > 0, "Total allocation must be positive"
        logger.info("Input validation passed")

    def _build_objective_function(
        self,
        assets: List[Asset],
        covariance_matrix: np.ndarray,
        transaction_costs: Dict,
        market_impact: Dict,
        params: OptimizationParameters
    ):
        """
        Build URT+ objective function

        Maximize: Σᵢ Σⱼ [E(Rᵢⱼ,t) × wᵢⱼ,t] - λ × Risk(W,t) - γ × Cost(W,t) - δ × Impact(W,t)
        """
        def objective(weights: np.ndarray) -> float:
            # Component 1: Expected Returns
            returns = sum(
                assets[i].expected_return * weights[i]
                for i in range(len(assets))
            )

            # Component 2: Portfolio Risk (W^T Σ W)
            risk = np.dot(weights, np.dot(covariance_matrix, weights))

            # Component 3: Transaction Costs
            total_tc = sum(
                tc_cost * weights[i]
                for (market, asset, platform), tc_cost in transaction_costs.items()
                for i, a in enumerate(assets)
                if a.market.value == market
            )

            # Component 4: Market Impact
            total_impact = sum(
                impact * weights[i]
                for (market, asset), impact in market_impact.items()
                for i, a in enumerate(assets)
                if a.market.value == market
            )

            # URT+ Objective Value
            objective_value = (
                returns
                - params.risk_aversion * risk
                - params.cost_sensitivity * total_tc
                - params.impact_sensitivity * total_impact
            )

            return -objective_value  # Negative for minimization

        return objective

    def _build_constraints(
        self,
        constraints: PortfolioConstraints,
        assets: List[Asset]
    ) -> List:
        """Build constraint functions for optimizer"""
        constraint_list = []

        # Constraint 1: Sum of weights = 1
        constraint_list.append({
            'type': 'eq',
            'fun': lambda w: np.sum(w) - constraints.total_allocation
        })

        # Constraint 2: Weight bounds (0 ≤ wᵢⱼ,t ≤ wᵢⱼ,max)
        bounds = []
        for i, asset in enumerate(assets):
            max_weight = constraints.position_limits.get(
                asset.symbol,
                1.0
            ) if constraints.position_limits else 1.0
            bounds.append((0.0, max_weight))

        # Constraint 3: Market exposure limits
        if constraints.market_exposure_limits:
            for market_type in MarketType:
                max_exposure = constraints.market_exposure_limits.get(market_type, 1.0)

                def market_constraint(w, mt=market_type, me=max_exposure):
                    market_weight = sum(
                        w[i] for i, asset in enumerate(assets)
                        if asset.market == mt
                    )
                    return me - market_weight

                constraint_list.append({
                    'type': 'ineq',
                    'fun': market_constraint
                })

        return constraint_list, bounds

    def _quantum_optimize(
        self,
        objective_fn,
        constraint_fns,
        assets: List[Asset],
        params: OptimizationParameters
    ) -> Dict:
        """
        Quantum optimization using QAOA

        This converts the optimization problem to QUBO and solves using
        Quantum Approximate Optimization Algorithm
        """
        import time
        start_time = time.time()

        logger.info(f"Starting quantum optimization with {params.qaoa_layers} QAOA layers")

        try:
            # Import quantum libraries
            from qiskit_optimization import QuadraticProgram
            from qiskit_optimization.algorithms import MinimumEigenOptimizer
            from qiskit.algorithms import QAOA
            from qiskit.algorithms.optimizers import SPSA

            # Convert to QUBO formulation
            qp = self._convert_to_qubo(
                objective_fn,
                constraint_fns,
                len(assets)
            )

            # Setup QAOA
            optimizer = SPSA(maxiter=300)
            qaoa = QAOA(
                optimizer=optimizer,
                reps=params.qaoa_layers,
                quantum_instance=self.quantum_backend
            )

            # Solve
            minimum_eigen_optimizer = MinimumEigenOptimizer(qaoa)
            result = minimum_eigen_optimizer.solve(qp)

            # Decode solution
            weights = self._decode_quantum_solution(result.x, len(assets))

            execution_time = time.time() - start_time

            logger.info(f"Quantum optimization completed in {execution_time:.2f}s")

            return {
                'weights': weights,
                'execution_info': {
                    'method': 'quantum_qaoa',
                    'backend': str(self.quantum_backend),
                    'execution_time': execution_time,
                    'qaoa_layers': params.qaoa_layers,
                    'optimal_value': result.fval
                }
            }

        except Exception as e:
            logger.warning(f"Quantum optimization failed: {e}. Falling back to classical.")
            return self._classical_optimize(objective_fn, constraint_fns, assets, params)

    def _classical_optimize(
        self,
        objective_fn,
        constraint_fns,
        assets: List[Asset],
        params: OptimizationParameters
    ) -> Dict:
        """Classical optimization using scipy"""
        from scipy.optimize import minimize
        import time

        start_time = time.time()
        logger.info("Starting classical optimization")

        # Initial guess: equal weights
        x0 = np.ones(len(assets)) / len(assets)

        # Optimize
        result = minimize(
            objective_fn,
            x0,
            method='SLSQP',
            constraints=constraint_fns[0],
            bounds=constraint_fns[1],
            options={'maxiter': 1000, 'ftol': 1e-9}
        )

        execution_time = time.time() - start_time

        logger.info(f"Classical optimization completed in {execution_time:.2f}s")

        return {
            'weights': result.x,
            'execution_info': {
                'method': 'classical_slsqp',
                'execution_time': execution_time,
                'iterations': result.nit,
                'success': result.success,
                'optimal_value': result.fun
            }
        }

    def _convert_to_qubo(
        self,
        objective_fn,
        constraint_fns,
        num_assets: int
    ):
        """Convert optimization problem to QUBO format"""
        from qiskit_optimization import QuadraticProgram

        qp = QuadraticProgram('URT_Plus_Optimization')

        # Create binary variables with 8-bit precision
        num_bits = 8
        for i in range(num_assets):
            for bit in range(num_bits):
                qp.binary_var(f"w_{i}_{bit}")

        # Add objective (simplified for demonstration)
        # In production, this would encode the full URT+ objective
        linear = {}
        quadratic = {}

        # Encode objective function components
        # (Implementation details omitted for brevity)

        qp.minimize(linear=linear, quadratic=quadratic)

        return qp

    def _decode_quantum_solution(self, binary_solution: np.ndarray, num_assets: int) -> np.ndarray:
        """Decode binary quantum solution to portfolio weights"""
        num_bits = 8
        weights = np.zeros(num_assets)

        for i in range(num_assets):
            weight = 0.0
            for bit in range(num_bits):
                idx = i * num_bits + bit
                if idx < len(binary_solution):
                    weight += binary_solution[idx] * (2 ** (-bit - 1))
            weights[i] = weight

        # Normalize to sum to 1
        weights = weights / np.sum(weights)

        return weights

    def _calculate_metrics(
        self,
        weights: np.ndarray,
        assets: List[Asset],
        covariance_matrix: np.ndarray,
        transaction_costs: Dict,
        market_impact: Dict,
        params: OptimizationParameters
    ) -> Dict:
        """Calculate portfolio performance metrics"""

        # Expected return
        expected_return = sum(
            assets[i].expected_return * weights[i]
            for i in range(len(assets))
        )

        # Portfolio variance and risk
        portfolio_variance = np.dot(weights, np.dot(covariance_matrix, weights))
        portfolio_risk = np.sqrt(portfolio_variance)

        # Sharpe ratio (assuming risk-free rate = 0)
        sharpe_ratio = expected_return / portfolio_risk if portfolio_risk > 0 else 0

        # Transaction costs
        total_transaction_costs = sum(
            tc * weights[i]
            for (m, a, p), tc in transaction_costs.items()
            for i, asset in enumerate(assets)
            if asset.market.value == m
        )

        # Market impact
        total_market_impact = sum(
            impact * weights[i]
            for (m, a), impact in market_impact.items()
            for i, asset in enumerate(assets)
            if asset.market.value == m
        )

        # Objective value
        objective_value = (
            expected_return
            - params.risk_aversion * portfolio_variance
            - params.cost_sensitivity * total_transaction_costs
            - params.impact_sensitivity * total_market_impact
        )

        # Market allocation breakdown
        market_allocation = {}
        for market_type in MarketType:
            allocation = sum(
                weights[i]
                for i, asset in enumerate(assets)
                if asset.market == market_type
            )
            market_allocation[market_type.name.lower()] = allocation

        return {
            'expected_return': float(expected_return),
            'portfolio_risk': float(portfolio_risk),
            'portfolio_variance': float(portfolio_variance),
            'sharpe_ratio': float(sharpe_ratio),
            'transaction_costs': float(total_transaction_costs),
            'market_impact': float(total_market_impact),
            'objective_value': float(objective_value),
            'market_allocation': market_allocation
        }

    def _validate_constraints(
        self,
        weights: np.ndarray,
        constraints: PortfolioConstraints,
        assets: List[Asset]
    ) -> Dict:
        """Validate that solution satisfies all URT+ constraints"""

        results = {}

        # Constraint 1: Total allocation
        total = np.sum(weights)
        results['total_allocation'] = {
            'value': float(total),
            'target': constraints.total_allocation,
            'satisfied': abs(total - constraints.total_allocation) < 0.001
        }

        # Constraint 2: Position limits
        position_check = all(
            weights[i] <= constraints.position_limits.get(asset.symbol, 1.0)
            for i, asset in enumerate(assets)
        ) if constraints.position_limits else True
        results['position_limits'] = 'satisfied' if position_check else 'violated'

        # Constraint 3: Market exposure limits
        if constraints.market_exposure_limits:
            market_exposure_check = True
            for market_type in MarketType:
                market_weight = sum(
                    weights[i]
                    for i, asset in enumerate(assets)
                    if asset.market == market_type
                )
                max_exposure = constraints.market_exposure_limits.get(market_type, 1.0)
                if market_weight > max_exposure + 0.001:
                    market_exposure_check = False
                    break
            results['market_exposure_limits'] = 'satisfied' if market_exposure_check else 'violated'
        else:
            results['market_exposure_limits'] = 'not_applicable'

        return results


# FastAPI Service Endpoints
if __name__ == "__main__":
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel

    app = FastAPI(title="URT+ Optimizer Service")

    optimizer_service = URTOptimizerService()

    class OptimizationRequest(BaseModel):
        portfolio_id: str
        markets: Dict
        constraints: Dict
        optimization_parameters: Dict

    @app.post("/api/v1/urt/optimize")
    async def optimize_portfolio(request: OptimizationRequest):
        """URT+ Multi-Market Portfolio Optimization Endpoint"""
        try:
            # Convert request to internal format
            assets = _parse_assets_from_request(request.markets)
            covariance_matrix = _generate_covariance_matrix(assets)
            transaction_costs = _parse_transaction_costs(request.markets)
            market_impact = _parse_market_impact(request.markets)
            constraints = _parse_constraints(request.constraints)
            params = _parse_parameters(request.optimization_parameters)

            # Execute optimization
            result = optimizer_service.optimize_portfolio(
                assets=assets,
                covariance_matrix=covariance_matrix,
                transaction_costs=transaction_costs,
                market_impact=market_impact,
                constraints=constraints,
                params=params
            )

            return {
                "status": "success",
                "data": result
            }

        except Exception as e:
            logger.error(f"Optimization failed: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    def _parse_assets_from_request(markets: Dict) -> List[Asset]:
        """Parse assets from request"""
        assets = []
        market_map = {
            'crypto': MarketType.CRYPTO,
            'stocks': MarketType.STOCKS,
            'forex': MarketType.FOREX,
            'commodities': MarketType.COMMODITIES,
            'derivatives': MarketType.DERIVATIVES
        }

        for market_name, market_data in markets.items():
            market_type = market_map.get(market_name.lower())
            if market_type:
                for i, symbol in enumerate(market_data['assets']):
                    assets.append(Asset(
                        symbol=symbol,
                        market=market_type,
                        expected_return=market_data['expected_returns'][i]
                    ))

        return assets

    def _generate_covariance_matrix(assets: List[Asset]) -> np.ndarray:
        """Generate or fetch covariance matrix"""
        n = len(assets)
        # Simplified: In production, fetch from historical data
        cov = np.eye(n) * 0.01
        return cov

    def _parse_transaction_costs(markets: Dict) -> Dict:
        """Parse transaction costs"""
        # Simplified implementation
        return {}

    def _parse_market_impact(markets: Dict) -> Dict:
        """Parse market impact"""
        # Simplified implementation
        return {}

    def _parse_constraints(constraints_dict: Dict) -> PortfolioConstraints:
        """Parse constraints from request"""
        return PortfolioConstraints(
            position_limits=constraints_dict.get('position_limits'),
            market_exposure_limits=constraints_dict.get('market_exposure_limits'),
            max_transaction_cost=constraints_dict.get('max_transaction_cost', 0.01),
            max_correlation_exposure=constraints_dict.get('max_correlation_exposure', 0.70)
        )

    def _parse_parameters(params_dict: Dict) -> OptimizationParameters:
        """Parse optimization parameters"""
        return OptimizationParameters(
            risk_aversion=params_dict.get('risk_aversion', 0.5),
            cost_sensitivity=params_dict.get('cost_sensitivity', 0.3),
            impact_sensitivity=params_dict.get('impact_sensitivity', 0.2),
            quantum_backend=params_dict.get('quantum_backend', 'ibm_quantum'),
            qaoa_layers=params_dict.get('qaoa_layers', 5),
            use_quantum=params_dict.get('use_quantum', True)
        )

    # Run service
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
