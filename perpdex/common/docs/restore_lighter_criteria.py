#!/usr/bin/env python3
"""
Restore missing Lighter completion criteria that was lost during duplicate removal
"""

def restore_lighter_criteria():
    with open("DEX_INTEGRATION_FRAMEWORK.md", 'r', encoding='utf-8') as f:
        content = f.read()

    # Content to restore (from FRAMEWORK_V2_2_CHANGELOG.md)
    lighter_section = '''

#### Apex Strategy Evolution

```yaml
apex_transition:
  current: Trend Following (EMA Crossover)
  reason: "빠른 검증 + 안정적 성능"

  next_strategy_evaluation:
    - Market Making: Volume 최적화 (50-100 trades/day)
    - Grid Trading: 안정적 volume (10-30 trades/day)
    - Delta Neutral (Volume Focus): 최고 volume (50-200 trades/day)

  decision_timeline: "1개월 실전 검증 후 결정"

lighter_preparation:
  keep: Trend Following
  reason: "Lighter는 Sharpe bonus 제공 (Sharpe > 5 시 30% 포인트 보너스)"
  why_trend_for_lighter: "Volume보다 Risk-adjusted return 중요, 거래수수료 무료 → 낮은 거래수도 OK"
  constraint: "⚠️ API Private Beta Permission 대기 중"
  why_apex_testing: "Permission 획득 즉시 배포 위해 Apex에서 완성도 높이기"
  status: "Apex 1개월 실전 검증 후 Lighter 배포 준비 완료"

  completion_criteria_detailed:
    backtest_validation:
      - Sharpe ratio > 3.0 (목표: 5.0 for 30% bonus)
      - Max drawdown < 15%
      - Win rate > 55%
      - Profit factor > 1.5
      - Monthly return > 10% (consistent)

    apex_실전_검증:
      - 1개월 실전 운영 (안정성 확인)
      - Sharpe > 3.0 유지 (실전에서도)
      - Max drawdown < 15% (실전에서도)
      - 시스템 안정성 (crashes, errors < 1%)
      - Trade execution quality (slippage < 0.1%)

    lighter_배포_준비:
      - API private beta permission 승인 대기 중
      - 승인 즉시 코드 배포 가능 (Apex 검증 완료)
      - 예상 Sharpe: 3.0-5.0 (Lighter fee-free 환경)
      - 포인트 보너스 목표: 30% (Sharpe > 5 달성 시)

    success_probability:
      - Apex 검증 통과 시 Lighter 성공 확률 > 80%
      - Sharpe 5.0 달성 시 Top 10% ranking 예상
      - Volume은 낮지만 ($40K-100K/month) point efficiency 높음
```
'''

    # Find insertion point: After first "Real Example: Apex" section
    # Look for the Apex characteristics section (around line 783-810)
    marker = '''```yaml
point_system:
  type: "Volume-based + TVL-based"
  volume_weight: 70%
  tvl_weight: 30%

fees:
  maker: 0.02%
  taker: 0.05%

characteristics:
  - High volume requirement (top 10% traders)
  - Capital efficiency important (leverage bonus)
  - Competitive environment
```'''

    insertion_pos = content.find(marker)

    if insertion_pos == -1:
        print("❌ Could not find insertion marker")
        return False

    # Find the end of the marker block
    insertion_pos = content.find('```', insertion_pos + len(marker))

    if insertion_pos == -1:
        print("❌ Could not find end of marker block")
        return False

    # Insert after the closing ```
    insertion_pos += 3  # Skip the ```

    # Insert the Lighter criteria section
    new_content = content[:insertion_pos] + lighter_section + content[insertion_pos:]

    # Save
    with open("DEX_INTEGRATION_FRAMEWORK.md", 'w', encoding='utf-8') as f:
        f.write(new_content)

    print("✅ Restored Lighter completion criteria section")

    # Verify
    with open("DEX_INTEGRATION_FRAMEWORK.md", 'r', encoding='utf-8') as f:
        verify_content = f.read()

    criteria_count = verify_content.count('completion_criteria_detailed')
    evolution_count = verify_content.count('Apex Strategy Evolution')
    lighter_prep_count = verify_content.count('lighter_preparation')

    print(f"\nVerification:")
    print(f"  - 'completion_criteria_detailed': {criteria_count} (should be 1) {'✅' if criteria_count == 1 else '❌'}")
    print(f"  - 'Apex Strategy Evolution': {evolution_count} (should be 1) {'✅' if evolution_count == 1 else '❌'}")
    print(f"  - 'lighter_preparation': {lighter_prep_count} (should be 1) {'✅' if lighter_prep_count == 1 else '❌'}")

    return criteria_count == 1 and evolution_count == 1 and lighter_prep_count == 1

if __name__ == '__main__':
    success = restore_lighter_criteria()
    if success:
        print("\n✅ Restoration completed successfully")
    else:
        print("\n❌ Restoration failed - manual intervention needed")
