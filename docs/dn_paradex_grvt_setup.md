# DN Hedge Bot: Paradex + GRVT Setup Guide

## Quick Start

```bash
# 1. Test connections
conda run -n quant python test_dn_paradex_grvt.py

# 2. Run bot (after setup)
conda run -n quant python hedge_mode.py --exchange paradex --ticker SOL --size 0.1 --iter 10
```

## Market Specifications

### Paradex SOL-USD-PERP
| Parameter | Value |
|-----------|-------|
| Contract | SOL-USD-PERP |
| Min Notional | $10 |
| Order Size Increment | 0.01 SOL |
| Tick Size | $0.001 |
| Maker Fee (API) | 0.003% |
| Taker Fee (API) | 0.02% |

### GRVT SOL_USDT_Perp
| Parameter | Value |
|-----------|-------|
| Contract | SOL_USDT_Perp |
| Min Size | 0.1 SOL (~$13.4 @ $134) |
| Tick Size | $0.01 |
| Maker Fee | TBD (account level) |
| Taker Fee | TBD (account level) |

## Required Budget

| Scenario | Minimum Budget |
|----------|----------------|
| Single iteration test | ~$25 (both exchanges) |
| 10 iterations with buffer | $50+ recommended |

## Environment Setup

### .env Configuration
```
# GRVT (already configured)
GRVT_TRADING_ACCOUNT_ID=<your account id>
GRVT_PRIVATE_KEY=<your private key>
GRVT_API_KEY=<your api key>

# Paradex (required)
PARADEX_L1_ADDRESS=0x<EVM wallet address>
PARADEX_L2_PRIVATE_KEY=0x<Paradex private key from app>
PARADEX_ENVIRONMENT=prod
```

### Getting Paradex Private Key
1. Go to https://app.paradex.trade
2. Connect your wallet
3. Click avatar (top right) → Wallet → Export Private Key

## Usage

### Basic Test (10 iterations)
```bash
conda run -n quant python hedge/hedge_mode_paradex_grvt.py \
  --ticker SOL \
  --size 0.1 \
  --iter 10
```

### Strategy Test Modes

| Test | Primary Mode | Hedge Mode | Command |
|------|--------------|------------|---------|
| Test 1 | bbo_minus_1 | market | `--primary-mode bbo_minus_1 --hedge-mode market` |
| Test 2 | bbo | market | `--primary-mode bbo --hedge-mode market` |
| Test 3 | bbo_minus_1 | bbo_minus_1 | `--primary-mode bbo_minus_1 --hedge-mode bbo_minus_1` |
| Test 4 | bbo | bbo | `--primary-mode bbo --hedge-mode bbo` |

## Fee Analysis

### Expected Costs per Round Trip (buy + sell)

**Paradex (PRIMARY) - Maker orders:**
- Fee: 0.003% × 2 = 0.006%
- On $13.4 trade: ~$0.0008

**GRVT (HEDGE) - Market orders:**
- Depends on account tier
- Typical: 0.02-0.05% taker

**Total per iteration:** ~0.03-0.06% (depends on GRVT fees)

## Logs

- Activity log: `logs/dn_paradex_grvt_SOL_log.txt`
- Trade CSV: `logs/dn_paradex_grvt_SOL_trades.csv`
