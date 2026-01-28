# Phase 8: Paradex Integration Plan

**Date**: October 24, 2025
**Status**: 📋 PLANNED (After Apex testnet completion)
**SDK**: `paradex-py` v0.4.9

---

## Overview

After completing Apex Pro testnet validation, we will integrate Paradex exchange for comparison and potential dual-exchange deployment.

---

## Prerequisites

### ✅ Completed
- [x] Apex Pro testnet validation (Static + Dynamic modes)
- [x] Mark price vs order book pricing logic fixed
- [x] Risk management validated
- [x] Logging and monitoring systems tested

### ⏳ Required Before Paradex
- [ ] Apex testnet results analyzed
- [ ] Paradex testnet account created
- [ ] Paradex API credentials obtained
- [ ] Paradex SDK installed (`pip install paradex-py`)

---

## Paradex SDK Installation

### Step 1: Install SDK
```bash
cd "perpdex farm"
pip install paradex-py==0.4.9
```

### Step 2: Verify Installation
```python
from paradex_py import Paradex
print("Paradex SDK installed successfully!")
```

---

## Paradex Architecture

### API Structure (Similar to Apex)

**Public API**:
- Market data (ticker, order book, trades)
- No authentication required

**Private API**:
- Account information
- Order management (place, cancel, query)
- Requires: Private key (Ethereum wallet)

### Authentication Method

**Paradex Uses Ethereum Wallet**:
```python
from paradex_py import Paradex

# Initialize with private key
client = Paradex(
    env='testnet',  # or 'mainnet'
    private_key=os.getenv('PARADEX_PRIVATE_KEY')
)
```

**Key Differences from Apex**:
- Apex: API Key + Secret + Passphrase + Omni Key
- Paradex: Ethereum Private Key only

---

## Implementation Plan

### Phase 8.1: Paradex Client Implementation

**File**: `apex/lib/paradex_client.py`

```python
"""
Paradex API Client Wrapper

Similar structure to ApexClient for consistency
"""

import os
from typing import Dict, List, Optional
from dotenv import load_dotenv
from paradex_py import Paradex


class ParadexClient:
    """
    Paradex API Client

    Testnet and mainnet support
    Public and Private API integration
    """

    def __init__(
        self,
        environment: str = 'mainnet',
        private_key: Optional[str] = None
    ):
        """
        Initialize Paradex client

        Args:
            environment: 'mainnet' or 'testnet'
            private_key: Ethereum private key (None = load from .env)
        """
        self.environment = environment.lower()

        # Load private key
        if private_key:
            self.private_key = private_key
        else:
            self.private_key = self._load_credentials()

        # Initialize Paradex client
        self.client = Paradex(
            env=self.environment,
            private_key=self.private_key
        )

    def _load_credentials(self) -> str:
        """Load private key from environment variables"""
        load_dotenv()

        private_key = os.getenv('PARADEX_PRIVATE_KEY')

        if not private_key:
            raise ValueError(
                ".env file requires PARADEX_PRIVATE_KEY\\n"
                "Get your Ethereum wallet private key for Paradex"
            )

        return private_key

    # ========== Public API Methods ==========

    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Get current ticker information"""
        try:
            return self.client.get_markets(market=symbol)
        except Exception as e:
            print(f"[ERROR] Failed to get ticker: {e}")
            return None

    def get_depth(self, symbol: str, limit: int = 20) -> Optional[Dict]:
        """Get order book depth"""
        try:
            result = self.client.get_orderbook(market=symbol, depth=limit)
            if result:
                # Normalize to standard format
                return {
                    'bids': result.get('bids', []),
                    'asks': result.get('asks', [])
                }
        except Exception as e:
            print(f"[ERROR] Failed to get depth: {e}")
            return None

    # ========== Private API Methods ==========

    def get_account(self) -> Optional[Dict]:
        """Get account information"""
        try:
            return self.client.get_account()
        except Exception as e:
            print(f"[ERROR] Failed to get account: {e}")
            return None

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        size: float,
        price: Optional[float] = None
    ) -> Optional[Dict]:
        """
        Place order

        Args:
            symbol: Market symbol (e.g., 'BTC-USD-PERP')
            side: 'BUY' or 'SELL'
            order_type: 'LIMIT' or 'MARKET'
            size: Order size
            price: Limit price (required for LIMIT orders)
        """
        try:
            return self.client.create_order(
                market=symbol,
                side=side.upper(),
                order_type=order_type.upper(),
                size=str(size),
                price=str(price) if price else None
            )
        except Exception as e:
            print(f"[ERROR] Failed to place order: {e}")
            return None

    def cancel_order(self, order_id: str) -> bool:
        """Cancel order by ID"""
        try:
            self.client.cancel_order(order_id=order_id)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to cancel order: {e}")
            return False

    def get_open_orders(self, symbol: Optional[str] = None) -> Optional[List[Dict]]:
        """Get open orders"""
        try:
            return self.client.get_orders(market=symbol) if symbol else self.client.get_orders()
        except Exception as e:
            print(f"[ERROR] Failed to get open orders: {e}")
            return None
```

### Phase 8.2: Avellaneda Client Adaptation

**File**: `apex/avellaneda_paradex_client.py`

```python
"""
Avellaneda Market Maker for Paradex

Reuses strategy logic from AvellanedaApexClient
"""

from apex.avellaneda_client import AvellanedaApexClient
from apex.lib.paradex_client import ParadexClient


class AvellanedaParadexClient(AvellanedaApexClient):
    """
    Paradex-specific Avellaneda implementation

    Inherits strategy logic from Apex implementation
    Only overrides exchange-specific methods
    """

    def __init__(
        self,
        environment: str = 'testnet',
        symbol: str = 'BTC-USD-PERP',
        params: AvellanedaParameters = None
    ):
        # Initialize base strategy
        super().__init__(environment, symbol, params)

        # Replace Apex client with Paradex client
        self.client = ParadexClient(environment=environment)

        # Symbol format adjustment
        # Paradex: BTC-USD-PERP
        # Apex: BTC-USDT
        self.symbol = symbol

    def _place_limit_order(self, side: str, price: float, size: float, post_only: bool = True):
        """
        Place limit order on Paradex

        Override to use Paradex API
        """
        try:
            order = self.client.place_order(
                symbol=self.symbol,
                side=side,
                order_type='LIMIT',
                size=size,
                price=price
            )
            return order
        except Exception as e:
            self.logger.error(f"Failed to place {side} limit order: {e}")
            return None
```

### Phase 8.3: Deployment Script

**File**: `apex/deploy_paradex_testnet.py`

```python
"""
Paradex Testnet Deployment Script

Similar to deploy_testnet.py but for Paradex
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from apex.avellaneda_paradex_client import AvellanedaParadexClient
from apex.avellaneda_client import AvellanedaParameters
from apex.monitor_dashboard import MonitoringDashboard
from common.trade_logger import TradeLogger, integrate_with_trading_client


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Paradex Testnet Deployment')

    parser.add_argument('--mode', type=str, choices=['static', 'dynamic'], required=True)
    parser.add_argument('--duration', type=int, default=3600)
    parser.add_argument('--symbol', type=str, default='BTC-USD-PERP')
    parser.add_argument('--position-limit', type=float, default=0.001)
    parser.add_argument('--max-daily-loss', type=float, default=1.0)
    parser.add_argument('--max-drawdown', type=float, default=5.0)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--environment', type=str, choices=['testnet', 'mainnet'], default='testnet')
    parser.add_argument('--yes', '-y', action='store_true')

    return parser.parse_args()


async def deploy(args):
    """Main deployment function"""
    print("\\n" + "="*80)
    print("AVELLANEDA MARKET MAKER - PARADEX TESTNET DEPLOYMENT")
    print("="*80)
    print(f"\\nMode:          {args.mode.upper()}")
    print(f"Symbol:        {args.symbol}")
    print(f"Duration:      {args.duration}s ({args.duration/3600:.1f}h)")
    print(f"Environment:   {args.environment.upper()}")
    print("="*80)

    # Create parameters
    params = AvellanedaParameters(
        gamma=0.1,
        sigma=0.02,
        k=1.5,
        eta=1.0,
        T=86400,
        position_limit=args.position_limit,
        max_daily_loss=args.max_daily_loss,
        max_total_drawdown=args.max_drawdown,
        use_dynamic_params=(args.mode == 'dynamic'),
        apex_maker_fee=0.0,  # Not used on Paradex
        paradex_maker_fee=0.0,  # 0% retail
        min_spread=0.0001,
        max_spread=0.005
    )

    # Initialize components
    print("\\n[INIT] Initializing Paradex components...")

    try:
        client = AvellanedaParadexClient(
            environment=args.environment,
            symbol=args.symbol,
            params=params
        )
        print(f"  [OK] Paradex client initialized")
    except Exception as e:
        print(f"  [X] Failed to initialize: {e}")
        return

    # Dashboard and logger (same as Apex)
    dashboard = MonitoringDashboard(refresh_interval=5.0)
    strategy_name = f"avellaneda_paradex_{args.mode}_{args.environment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    logger = TradeLogger(base_dir="logs/data", strategy_name=strategy_name)
    integrate_with_trading_client(client, logger)

    dashboard.start_console_display()

    # Run strategy
    print(f"\\n[RUN] Starting {args.mode} strategy on Paradex...")
    try:
        await client.run_strategy(duration=args.duration)
        print(f"\\n[COMPLETE] Strategy execution finished")
    except KeyboardInterrupt:
        print(f"\\n\\n[INTERRUPT] User interrupted")
    except Exception as e:
        print(f"\\n\\n[ERROR] Strategy failed: {e}")
    finally:
        dashboard.stop_console_display()
        logger.flush()

        stats = logger.get_summary_stats()
        print(f"\\n[STATS] Final Statistics:")
        print(f"  Total Trades:  {stats['total_trades']}")
        print(f"  Win Rate:      {stats['win_rate']:.1f}%")
        print(f"  Net P&L:       ${stats['net_pnl']:.2f}")

    print("\\n" + "="*80)
    print("PARADEX DEPLOYMENT COMPLETE")
    print("="*80 + "\\n")


def main():
    """Main entry point"""
    load_dotenv()
    args = parse_args()

    # Check Paradex private key
    if not os.getenv('PARADEX_PRIVATE_KEY'):
        print("[X] PARADEX_PRIVATE_KEY not found in .env")
        print("    Add your Ethereum wallet private key:")
        print("    PARADEX_PRIVATE_KEY=0x...")
        sys.exit(1)

    try:
        asyncio.run(deploy(args))
    except Exception as e:
        print(f"\\n[X] Deployment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

## Environment Variables

### Update `.env` File

```bash
# Existing Apex Pro credentials
APEX_API_KEY=your_apex_key
APEX_API_SECRET=your_apex_secret
APEX_API_PASSPHRASE=your_apex_passphrase
APEX_ZK_SEEDS=your_omni_key
APEX_ZK_L2KEY=your_omni_key

# NEW: Paradex credentials
PARADEX_PRIVATE_KEY=0x...your_ethereum_private_key_here
```

**How to get Paradex testnet key**:
1. Create Ethereum wallet (MetaMask, etc.)
2. Connect to Paradex testnet
3. Export private key from wallet
4. Add to `.env` file

---

## Execution Plan

### After Apex Testnet Completes

**Step 1: Analysis**
```bash
# Analyze Apex testnet results
python apex/analyze_results.py \
  --static testnet_static_1hour_fixed.log \
  --dynamic testnet_dynamic_1hour.log
```

**Step 2: Paradex Setup**
```bash
# Install Paradex SDK
pip install paradex-py==0.4.9

# Create Paradex account at https://testnet.paradex.trade
# Export private key and add to .env
```

**Step 3: Implement Paradex Client**
```bash
# Create files
touch apex/lib/paradex_client.py
touch apex/avellaneda_paradex_client.py
touch apex/deploy_paradex_testnet.py
```

**Step 4: Test Paradex Static Mode**
```bash
python apex/deploy_paradex_testnet.py \
  --mode static \
  --duration 3600 \
  --yes
```

**Step 5: Test Paradex Dynamic Mode**
```bash
python apex/deploy_paradex_testnet.py \
  --mode dynamic \
  --duration 3600 \
  --yes
```

---

## Comparison Framework

### After Both Testnets Complete

**Metrics to Compare**:
1. **Fill Rate**: Which exchange fills more orders?
2. **Fees**: Actual fees paid (Apex: 0.02%, Paradex: 0%)
3. **Slippage**: Price improvement/degradation
4. **Latency**: Order placement to confirmation time
5. **Stability**: API uptime and reliability
6. **Liquidity**: Order book depth and spread

**Decision Matrix**:
```
IF paradex_fill_rate > apex_fill_rate * 1.2:
    → Deploy on Paradex (better liquidity)
ELIF paradex_fees < apex_fees:
    → Deploy on Paradex (cost advantage)
ELIF apex_stability > paradex_stability:
    → Deploy on Apex (reliability)
ELSE:
    → Deploy on BOTH (diversification)
```

---

## Key Differences: Apex vs Paradex

| Feature | Apex Pro | Paradex |
|---------|----------|---------|
| **Auth** | API Key + Omni Key | Ethereum Private Key |
| **Maker Fee** | 0.02% | 0% (retail) or -0.05% (RPI) |
| **Taker Fee** | 0.05% | 0.025% |
| **Testnet** | Arbitrum | Ethereum Sepolia |
| **Mainnet** | Arbitrum | Ethereum |
| **Symbol Format** | BTC-USDT | BTC-USD-PERP |
| **SDK** | apexomni | paradex-py |

---

## Timeline

**Estimated Time**:
- Apex testnet completion: ~40 minutes (from now)
- Paradex implementation: ~2 hours
- Paradex testnet deployment: 2 hours (Static + Dynamic)
- Analysis and comparison: 1 hour

**Total**: ~5-6 hours for complete dual-exchange validation

---

## Success Criteria

### Paradex Integration Complete When:
- [ ] Paradex SDK installed
- [ ] ParadexClient implemented and tested
- [ ] AvellanedaParadexClient working
- [ ] Paradex testnet deployment successful (Static mode)
- [ ] Paradex testnet deployment successful (Dynamic mode)
- [ ] Comparison analysis completed
- [ ] Exchange selection decision made

---

## Next Steps

1. **Now**: Wait for Apex testnet to complete (~40 minutes)
2. **Then**: Analyze Apex results
3. **Then**: Install Paradex SDK
4. **Then**: Implement Paradex client
5. **Then**: Deploy to Paradex testnet
6. **Finally**: Compare and choose exchange(s)

---

*Prepared: October 24, 2025*
*Status: Ready to execute after Apex testnet completion*
*Next: Paradex implementation and testing*
