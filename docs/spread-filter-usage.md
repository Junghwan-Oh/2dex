# Spread Filter Optimization - User Guide
# 스프레드 필터 최적화 - 사용자 가이드

## Overview / 개요

### English
The spread filter optimization implements a configurable minimum spread threshold to improve trading efficiency:

- **6 bps minimum spread filter** (configurable via CLI)
- **POST_ONLY mode enabled by default** (2 bps maker fee)
- **Replaces previous 20 bps hardcoded filter**

This optimization reduces fee costs by 60% while maintaining acceptable trade frequency.

### 한국어
스프레드 필터 최적화는 거래 효율을 개선하기 위해 구성 가능한 최소 스프레드 임계값을 구현합니다:

- **6 bps 최소 스프레드 필터** (CLI 통해 구성 가능)
- **기본적으로 POST_ONLY 모드 활성화** (2 bps 메이커 수수료)
- **이전 20 bps 하드코딩된 필터를 대체**

이 최적화는 수락할 수 있는 거래 빈도를 유지하면서 수수료 비용을 60% 절감합니다.

---

## CLI Parameters / CLI 매개변수

| Parameter / 매개변수 | Type / 타입 | Default / 기본값 | Description / 설명 |
|---------------------|-------------|------------------|-------------------|
| `--min-spread-bps` | int / 정수 | 6 | Minimum spread in bps to enter trade / 거래 진입 최소 스프레드 (bps) |
| `--use-ioc` | flag / 플래그 | False | Use IOC mode (5 bps taker) instead of POST_ONLY / POST_ONLY 대신 IOC 모드 사용 (5 bps 테이커) |

---

## Usage Examples / 사용 예시

### Default Configuration / 기본 구성

```bash
# English: Default: 6 bps filter, POST_ONLY mode
# 한국어: 기본값: 6 bps 필터, POST_ONLY 모드
python3 hedge/DN_pair_eth_sol_nado.py --size 5000 --iter 100
```

### Custom Spread Filter / 사용자 정의 스프레드 필터

```bash
# English: Custom spread filter (10 bps)
# 한국어: 사용자 정의 스프레드 필터 (10 bps)
python3 hedge/DN_pair_eth_sol_nado.py --size 5000 --iter 100 --min-spread-bps 10
```

### IOC Mode / IOC 모드

```bash
# English: IOC mode for higher fill rate
# 한국어: 더 높은 체결률을 위한 IOC 모드
python3 hedge/DN_pair_eth_sol_nado.py --size 5000 --iter 100 --use-ioc
```

### Combined Options / 결합 옵션

```bash
# English: Combined: custom filter with IOC
# 한국어: 결합: IOC와 사용자 정의 필터
python3 hedge/DN_pair_eth_sol_nado.py --size 5000 --iter 100 --min-spread-bps 8 --use-ioc
```

---

## Expected Results / 예상 결과

### Performance Metrics / 성능 지표

| Metric / 지표 | Value / 값 | Description / 설명 |
|---------------|------------|-------------------|
| **Trade Frequency** / **거래 빈도** | 20-40 cycles/day | Daily trading cycles / 일일 거래 사이클 |
| **Fill Rate (POST_ONLY)** / **체결률 (POST_ONLY)** | 60-80% | Order fill percentage / 주문 체결 비율 |
| **Fee Reduction** / **수수료 절감** | 60% | POST_ONLY (2 bps) vs IOC (5 bps) / POST_ONLY 대비 IOC 수수료 절감율 |

### English
The POST_ONLY mode provides significant cost savings with a slightly lower fill rate compared to IOC mode. Choose based on your priorities:

- **POST_ONLY**: Lower fees (2 bps), lower fill rate (60-80%)
- **IOC**: Higher fees (5 bps), higher fill rate (~95%)

### 한국어
POST_ONLY 모드는 IOC 모드와 비교하여 약간 낮은 체결률로 상당한 비용 절감을 제공합니다. 우선순위에 따라 선택하세요:

- **POST_ONLY**: 낮은 수수료 (2 bps), 낮은 체결률 (60-80%)
- **IOC**: 높은 수수료 (5 bps), 높은 체결률 (~95%)

---

## Monitoring / 모니터링

### Check Trade Count / 거래 횟수 확인

```bash
# English: Check trade count
# 한국어: 거래 횟수 확인
tail -100 logs/DN_pair_eth_sol_nado_log.txt | grep "BUILD.*SUCCESS" | wc -l
```

### Check Spread Statistics / 스프레드 통계 확인

```bash
# English: Check spread statistics
# 한국어: 스프레드 통계 확인
tail -100 logs/DN_pair_eth_sol_nado_log.txt | grep "\[SPREAD\]"
```

### Check PNL / PNL 확인

```bash
# English: Check PNL
# 한국어: PNL 확인
tail -50 logs/DN_pair_eth_sol_nado_trades.csv
```

### Log Output Format / 로그 출력 형식

```
[SPREAD] Current: 8.5 bps | Min: 6.0 bps | Status: ACCEPT
[SPREAD] 현재: 8.5 bps | 최소: 6.0 bps | 상태: 승인
```

---

## Rollback / 롤백

### English
If you need to revert to the previous behavior (20 bps filter with IOC mode), use the CLI flags:

### 한국어
이전 동작(IOC 모드의 20 bps 필터)으로 되돌려야 하는 경우 CLI 플래그를 사용하세요:

```bash
# English: Use CLI flags (preferred) - replicates old behavior
# 한국어: CLI 플래그 사용 (권장) - 이전 동작 복제
python3 hedge/DN_pair_eth_sol_nado.py --size 5000 --iter 100 --min-spread-bps 20 --use-ioc
```

---

## Configuration Tips / 구성 팁

### English
1. **Start with defaults**: The 6 bps / POST_ONLY configuration is optimized for most scenarios
2. **Adjust based on market conditions**: Increase `--min-spread-bps` during volatile periods
3. **Monitor fill rates**: If fill rate drops below 50%, consider switching to IOC mode
4. **Track PNL impact**: Compare fee savings vs. missed opportunities

### 한국어
1. **기본값으로 시작**: 6 bps / POST_ONLY 구성은 대부분의 시나리오에 최적화되어 있습니다
2. **시장 상황에 따라 조정**: 변동성이 큰 기간에는 `--min-spread-bps`를 늘리세요
3. **체결률 모니터링**: 체결률이 50% 미만으로 떨어지면 IOC 모드로 전환을 고려하세요
4. **PNL 영향 추적**: 수수료 절감 vs 놓친 기회 비교

---

## Troubleshooting / 문제 해결

### Common Issues / 일반적인 문제

| Issue / 문제 | Solution / 해결책 |
|--------------|-------------------|
| **Low fill rate** / **낮은 체결률 | Add `--use-ioc` flag or reduce `--min-spread-bps` / `--use-ioc` 플래그 추가 또는 `--min-spread-bps` 감소 |
| **No trades executing** / **거래 실행 안됨 | Reduce `--min-spread-bps` value / `--min-spread-bps` 값 감소 |
| **High fee costs** / **높은 수수료 비용 | Remove `--use-ioc` flag (use POST_ONLY) / `--use-ioc` 플래그 제거 (POST_ONLY 사용) |

---

## Summary / 요약

### English
The spread filter optimization provides flexible configuration for trading efficiency:

- Default: **6 bps minimum spread** with **POST_ONLY mode** (2 bps fees)
- Fully configurable via **CLI parameters**
- **60% fee reduction** compared to IOC mode
- Easy **rollback** to previous behavior if needed

### 한국어
스프레드 필터 최적화는 거래 효율성을 위한 유연한 구성을 제공합니다:

- 기본값: **POST_ONLY 모드**의 **6 bps 최소 스프레드** (2 bps 수수료)
- **CLI 매개변수**를 통한 완전한 구성 가능
- IOC 모드 대비 **60% 수수료 절감**
- 필요한 경우 이전 동작으로 쉬운 **롤백**
