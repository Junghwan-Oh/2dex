"""
터미널 출력 포매팅 유틸리티

포지션 정보 및 계좌 요약을 보기 좋게 출력하는 함수 모음
"""

from typing import Dict, List, Optional, Tuple


def format_price(price: float, decimals: int = 2, currency: str = 'USDT') -> str:
    """
    가격 포매팅 (천 단위 콤마, 통화 표시)

    Args:
        price: 가격
        decimals: 소수점 자리수 (기본값: 2)
        currency: 통화 단위 (기본값: 'USDT')

    Returns:
        포매팅된 가격 문자열

    Example:
        >>> format_price(123456.789)
        '$123,456.79 USDT'
    """
    if currency:
        return f"${price:,.{decimals}f} {currency}"
    return f"${price:,.{decimals}f}"


def format_percentage(value: float, decimals: int = 2, with_sign: bool = True) -> str:
    """
    퍼센트 포매팅 (+/- 부호 포함)

    Args:
        value: 퍼센트 값
        decimals: 소수점 자리수 (기본값: 2)
        with_sign: 양수일 때 + 부호 표시 여부 (기본값: True)

    Returns:
        포매팅된 퍼센트 문자열

    Example:
        >>> format_percentage(12.34)
        '+12.34%'
    """
    sign = '+' if value > 0 and with_sign else ''
    return f"{sign}{value:.{decimals}f}%"


def format_position_info(
    position: Dict,
    ticker_info: Optional[Dict] = None,
    initial_margin: float = 0,
    maintenance_margin: float = 0,
    index: int = 1
) -> str:
    """
    개별 포지션 정보를 포매팅된 문자열로 변환

    Args:
        position: 포지션 딕셔너리 (symbol, side, size, entryPrice 등)
        ticker_info: 현재가 정보 딕셔너리 (lastPrice, markPrice, indexPrice)
        initial_margin: 초기 마진 (USDT)
        maintenance_margin: 유지 마진 (USDT)
        index: 포지션 번호 (여러 포지션이 있을 때)

    Returns:
        포매팅된 포지션 정보 문자열
    """
    from .position_calculator import (
        calculate_liquidation_price,
        calculate_unrealized_pnl,
        calculate_distance_to_liquidation,
        calculate_leverage,
        calculate_margin_usage,
        calculate_pnl_percentage
    )

    # 기본 정보 추출
    symbol = position.get('symbol', 'N/A')
    side = position.get('side', 'N/A')
    size = float(position.get('size', '0'))
    entry_price = float(position.get('entryPrice', '0'))
    fee = float(position.get('fee', '0'))
    funding_fee = float(position.get('fundingFee', '0'))
    margin_rate = float(position.get('customInitialMarginRate', '0'))

    # Position value in USDT
    position_value_usdt = size * entry_price

    # 레버리지 및 마진 계산
    leverage = calculate_leverage(margin_rate)
    margin_used = calculate_margin_usage(position_value_usdt, margin_rate)

    # 출력 시작
    lines = [f"\n   [{index}] {symbol}"]
    lines.append(f"      - Side: {side}")
    lines.append(f"      - Size: {size} BTC")
    lines.append(f"      - Position Value: {format_price(position_value_usdt)}")
    lines.append(f"      - Entry Price: {format_price(entry_price)}")

    # 현재가 정보가 있으면 추가 정보 표시
    if ticker_info:
        mark_price = ticker_info.get('markPrice', 0)
        last_price = ticker_info.get('lastPrice', 0)
        current_price = mark_price if mark_price > 0 else last_price

        if current_price > 0:
            lines.append(f"      - Mark Price: {format_price(current_price)}")

            # 미실현 손익 계산
            unrealized_pnl = calculate_unrealized_pnl(side, entry_price, current_price, size)
            lines.append(f"      - Unrealized PnL: {unrealized_pnl:+.6f} USDT")

            # PnL 퍼센트
            if margin_used > 0:
                pnl_percent = calculate_pnl_percentage(unrealized_pnl, margin_used)
                lines.append(f"      - PnL % (vs Margin): {format_percentage(pnl_percent)}")

            # 청산가 계산
            if initial_margin > 0 and maintenance_margin > 0:
                liquidation_price = calculate_liquidation_price(
                    side, entry_price, size, initial_margin, maintenance_margin
                )

                if liquidation_price > 0:
                    lines.append(f"      - Liquidation Price: {format_price(liquidation_price)}")

                    # 청산가까지 거리
                    distance_pct, direction = calculate_distance_to_liquidation(
                        side, current_price, liquidation_price
                    )
                    lines.append(f"      - Distance to Liquidation: {format_percentage(distance_pct, with_sign=False)} ({direction})")

    # 레버리지 및 마진 정보
    lines.append(f"      - Leverage: {leverage:.1f}x")
    lines.append(f"      - Margin Used: {format_price(margin_used)}")
    lines.append(f"      - Fee Paid: {fee:.6f} USDT")
    lines.append(f"      - Funding Fee: {funding_fee:.6f} USDT")

    return '\n'.join(lines)


def format_account_summary(
    account_id: str,
    ethereum_address: str,
    taker_fee: float,
    maker_fee: float,
    usdt_balance: float = 0,
    total_equity: float = 0,
    available_balance: float = 0,
    unrealized_pnl: float = 0,
    initial_margin: float = 0,
    maintenance_margin: float = 0
) -> str:
    """
    계좌 요약 정보를 포매팅된 문자열로 변환

    Args:
        account_id: 계좌 ID
        ethereum_address: 이더리움 주소
        taker_fee: Taker 수수료율 (0-1 범위)
        maker_fee: Maker 수수료율 (0-1 범위)
        usdt_balance: USDT 잔액
        total_equity: 총 자산 가치
        available_balance: 사용 가능 잔액
        unrealized_pnl: 미실현 손익
        initial_margin: 초기 마진
        maintenance_margin: 유지 마진

    Returns:
        포매팅된 계좌 요약 문자열
    """
    lines = []

    # 계좌 기본 정보
    lines.append("\n   [계좌 정보]")
    lines.append(f"   - Account ID: {account_id}")

    if ethereum_address and ethereum_address != 'N/A':
        # 이더리움 주소 축약 표시
        shortened = f"{ethereum_address[:6]}...{ethereum_address[-4:]}"
        lines.append(f"   - Ethereum Address: {shortened}")

    # 수수료 정보
    lines.append("\n   [수수료 정보]")
    lines.append(f"   - Taker Fee: {format_percentage(taker_fee * 100, decimals=4)}")
    lines.append(f"   - Maker Fee: {format_percentage(maker_fee * 100, decimals=4)}")

    # 잔액 정보
    if usdt_balance > 0:
        lines.append("\n   [계좌 잔액]")
        lines.append(f"   - USDT Balance: {usdt_balance}")

    # 계좌 요약 (마진 정보)
    if total_equity > 0:
        lines.append("\n   [계좌 요약]")
        lines.append(f"   - Total Equity: {total_equity:,.6f} USDT")
        lines.append(f"   - Available Balance: {available_balance:,.6f} USDT")
        lines.append(f"   - Total Unrealized PnL: {unrealized_pnl:+,.6f} USDT")
        lines.append(f"   - Initial Margin: {initial_margin:,.6f} USDT")
        lines.append(f"   - Maintenance Margin: {maintenance_margin:,.6f} USDT")

    return '\n'.join(lines)


def format_positions_list(
    positions: List[Dict],
    ticker_info_dict: Dict[str, Dict],
    initial_margin: float,
    maintenance_margin: float
) -> str:
    """
    여러 포지션을 리스트 형태로 포매팅

    Args:
        positions: 포지션 딕셔너리 리스트
        ticker_info_dict: 심볼별 현재가 정보 딕셔너리
        initial_margin: 초기 마진 (USDT)
        maintenance_margin: 유지 마진 (USDT)

    Returns:
        포매팅된 포지션 리스트 문자열
    """
    if not positions:
        return "\n   [열린 포지션: 0개]"

    lines = [f"\n   [열린 포지션: {len(positions)}개]"]

    for idx, position in enumerate(positions, 1):
        symbol = position.get('symbol', 'N/A')
        ticker_info = ticker_info_dict.get(symbol, {})

        position_str = format_position_info(
            position=position,
            ticker_info=ticker_info,
            initial_margin=initial_margin,
            maintenance_margin=maintenance_margin,
            index=idx
        )
        lines.append(position_str)

    return '\n'.join(lines)


def print_separator(char: str = '=', length: int = 60) -> None:
    """
    구분선 출력

    Args:
        char: 구분선 문자 (기본값: '=')
        length: 구분선 길이 (기본값: 60)
    """
    print(char * length)


def print_section_header(title: str) -> None:
    """
    섹션 헤더 출력

    Args:
        title: 섹션 제목
    """
    print(f"\n[{title}]")
