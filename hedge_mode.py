#!/usr/bin/env python3
"""
Hedge Mode Entry Point

This script serves as the main entry point for hedge mode trading.
It imports and runs the appropriate hedge mode implementation based on the exchange parameter.

Usage:
    python hedge_mode.py --exchange <exchange> [other arguments]
    python hedge_mode.py --primary <exchange> --hedge <exchange> [other arguments]

Supported exchanges:
    - backpack: Uses HedgeBot from hedge_mode_bp.py (Backpack + Lighter)
    - extended: Uses HedgeBot from hedge_mode_ext.py (Extended + Lighter)
    - apex: Uses HedgeBot from hedge_mode_apex.py (Apex + Lighter)
    - grvt: Uses HedgeBot from hedge_mode_grvt.py (GRVT + Lighter)
      Use --v2 flag to use hedge_mode_grvt_v2.py instead
    - edgex: Uses HedgeBot from hedge_mode_edgex.py (edgeX + Lighter)
    - nado: Uses HedgeBot from hedge_mode_nado.py (Nado + Lighter)

2DEX Mode (Dynamic):
    Use --primary and --hedge to specify any two exchanges dynamically.
    PRIMARY exchange places maker orders (POST_ONLY), HEDGE places taker orders.
    Example: python hedge_mode.py --primary grvt --hedge backpack --ticker ETH --size 0.01 --iter 10

Cross-platform compatibility:
    - Works on Linux, macOS, and Windows
    - Direct imports instead of subprocess calls for better performance
"""

import asyncio
import sys
import argparse
from decimal import Decimal
from pathlib import Path
import dotenv


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Hedge Mode Trading Bot Entry Point",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python hedge_mode.py --exchange backpack --ticker BTC --size 0.002 --iter 10
    python hedge_mode.py --exchange extended --ticker ETH --size 0.1 --iter 5
    python hedge_mode.py --exchange apex --ticker BTC --size 0.002 --iter 10
    python hedge_mode.py --exchange grvt --ticker BTC --size 0.05 --iter 10 --max-position 0.1
    python hedge_mode.py --exchange grvt --v2 --ticker BTC --size 0.05 --iter 10 --max-position 0.1
    python hedge_mode.py --exchange edgex --ticker BTC --size 0.001 --iter 20
    python hedge_mode.py --exchange nado --ticker BTC --size 0.003 --iter 20 --max-position 0.05
    python hedge_mode.py --exchange paradex --ticker SOL --size 0.1 --iter 10

2DEX Mode (Dynamic - any two exchanges):
    python hedge_mode.py --primary grvt --hedge backpack --ticker ETH --size 0.01 --iter 10
    python hedge_mode.py --primary edgex --hedge nado --ticker BTC --size 0.001 --iter 20
        """,
    )

    parser.add_argument(
        "--exchange",
        type=str,
        default=None,
        help="Exchange to use (backpack, extended, apex, grvt, edgex, nado) - legacy mode",
    )
    parser.add_argument(
        "--primary",
        type=str,
        default=None,
        help="PRIMARY exchange for maker orders (2DEX mode)",
    )
    parser.add_argument(
        "--hedge",
        type=str,
        default=None,
        help="HEDGE exchange for taker orders (2DEX mode)",
    )
    parser.add_argument(
        "--ticker", type=str, default="BTC", help="Ticker symbol (default: BTC)"
    )
    parser.add_argument(
        "--size", type=str, required=True, help="Number of tokens to buy/sell per order"
    )
    parser.add_argument(
        "--iter", type=int, required=True, help="Number of iterations to run"
    )
    parser.add_argument(
        "--fill-timeout",
        type=int,
        default=5,
        help="Timeout in seconds for maker order fills (default: 5)",
    )
    parser.add_argument(
        "--sleep",
        type=int,
        default=0,
        help="Sleep time in seconds after each step (default: 0)",
    )
    parser.add_argument(
        "--env-file", type=str, default=".env", help=".env file path (default: .env)"
    )
    parser.add_argument(
        "--max-position",
        type=Decimal,
        default=Decimal("0"),
        help="Maximum position to hold (default: 0)",
    )
    parser.add_argument(
        "--v2",
        action="store_true",
        help="Use v2 implementation (currently only supported for grvt exchange)",
    )

    return parser.parse_args()


def validate_exchange(exchange):
    """Validate that the exchange is supported."""
    supported_exchanges = [
        "backpack",
        "extended",
        "apex",
        "grvt",
        "edgex",
        "nado",
        "paradex",
    ]
    if exchange.lower() not in supported_exchanges:
        print(f"Error: Unsupported exchange '{exchange}'")
        print(f"Supported exchanges: {', '.join(supported_exchanges)}")
        sys.exit(1)


def get_hedge_bot_class(exchange, v2=False):
    """Import and return the appropriate HedgeBot class."""
    try:
        if exchange.lower() == "backpack":
            from hedge.hedge_mode_bp import HedgeBot

            return HedgeBot
        elif exchange.lower() == "extended":
            from hedge.hedge_mode_ext import HedgeBot

            return HedgeBot
        elif exchange.lower() == "apex":
            from hedge.hedge_mode_apex import HedgeBot

            return HedgeBot
        elif exchange.lower() == "grvt":
            if v2:
                from hedge.hedge_mode_grvt_v2 import HedgeBot
            else:
                from hedge.hedge_mode_grvt import HedgeBot
            return HedgeBot
        elif exchange.lower() == "edgex":
            from hedge.hedge_mode_edgex import HedgeBot

            return HedgeBot
        elif exchange.lower() == "nado":
            from hedge.hedge_mode_nado import HedgeBot

            return HedgeBot
        elif exchange.lower() == "paradex":
            from hedge.hedge_mode_paradex_grvt import DNHedgeBot

            return DNHedgeBot
        else:
            raise ValueError(f"Unsupported exchange: {exchange}")
    except ImportError as e:
        print(f"Error importing hedge mode implementation: {e}")
        sys.exit(1)


async def main():
    """Main entry point that creates and runs the appropriate hedge bot."""
    args = parse_arguments()

    env_path = Path(args.env_file)
    if not env_path.exists():
        print(f"Env file not find: {env_path.resolve()}")
        sys.exit(1)
    dotenv.load_dotenv(args.env_file)

    # =====================================================
    # 2DEX Mode: --primary + --hedge (Dynamic two exchanges)
    # =====================================================
    if args.primary and args.hedge:
        from hedge.hedge_mode_2dex import HedgeBot2DEX

        print(f"Starting 2DEX hedge mode: PRIMARY={args.primary}, HEDGE={args.hedge}")
        print(f"Ticker: {args.ticker}, Size: {args.size}, Iterations: {args.iter}")
        print("-" * 50)

        try:
            bot = HedgeBot2DEX(
                primaryExchange=args.primary.lower(),
                hedgeExchange=args.hedge.lower(),
                ticker=args.ticker.upper(),
                orderQuantity=Decimal(args.size),
                fillTimeout=args.fill_timeout,
                iterations=args.iter,
                sleepTime=args.sleep,
                maxPosition=args.max_position,
            )
            await bot.run()
        except KeyboardInterrupt:
            print("\n2DEX hedge mode interrupted by user")
            return 1
        except Exception as e:
            print(f"Error running 2DEX hedge mode: {e}")
            import traceback

            print(f"Full traceback: {traceback.format_exc()}")
            return 1

        return 0

    # =====================================================
    # Legacy Mode: --exchange (Single exchange + Lighter)
    # =====================================================
    if not args.exchange:
        print("Error: Must specify either --exchange OR both --primary and --hedge")
        sys.exit(1)

    # Validate exchange
    validate_exchange(args.exchange)

    # Validate v2 flag usage
    if args.v2 and args.exchange.lower() != "grvt":
        print(f"Error: --v2 flag is only supported for grvt exchange")
        sys.exit(1)

    # Get the appropriate HedgeBot class
    try:
        HedgeBotClass = get_hedge_bot_class(args.exchange, v2=args.v2)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    version_str = " v2" if args.v2 else ""
    print(f"Starting hedge mode for {args.exchange} exchange{version_str}...")
    print(f"Ticker: {args.ticker}, Size: {args.size}, Iterations: {args.iter}")
    print("-" * 50)

    try:
        # v2 bot has different constructor signature (no iterations/sleep_time)
        if args.v2 and args.exchange.lower() == "grvt":
            bot = HedgeBotClass(
                ticker=args.ticker.upper(),
                order_quantity=Decimal(args.size),
                fill_timeout=args.fill_timeout,
                max_position=args.max_position,
            )
        elif args.exchange in ["backpack", "edgex", "nado", "grvt"]:
            bot = HedgeBotClass(
                ticker=args.ticker.upper(),
                order_quantity=Decimal(args.size),
                fill_timeout=args.fill_timeout,
                iterations=args.iter,
                sleep_time=args.sleep,
                max_position=args.max_position,
            )
        elif args.exchange == "paradex":
            bot = HedgeBotClass(
                ticker=args.ticker.upper(),
                order_quantity=Decimal(args.size),
                fill_timeout=args.fill_timeout,
                iterations=args.iter,
                sleep_time=args.sleep,
                max_position=args.max_position,
            )
        else:
            bot = HedgeBotClass(
                ticker=args.ticker.upper(),
                order_quantity=Decimal(args.size),
                fill_timeout=args.fill_timeout,
                iterations=args.iter,
                sleep_time=args.sleep,
            )

        # Run the bot
        await bot.run()

    except KeyboardInterrupt:
        print("\nHedge mode interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running hedge mode: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
