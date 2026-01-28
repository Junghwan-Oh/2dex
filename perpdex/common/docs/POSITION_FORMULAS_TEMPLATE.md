# 포지션 계산 공식 (템플릿)

Perpetual DEX 공통 포지션 계산 공식 템플릿입니다.

> **사용 방법**: 이 템플릿을 각 DEX 폴더로 복사하고, `{DEX_SPECIFIC}` placeholder를 해당 DEX의 실제 값으로 변경하세요.

## 목차
- [청산가 (Liquidation Price)](#청산가-liquidation-price)
- [미실현 손익 (Unrealized PnL)](#미실현-손익-unrealized-pnl)
- [레버리지 (Leverage)](#레버리지-leverage)
- [마진 사용량 (Margin Usage)](#마진-사용량-margin-usage)
- [청산까지 거리 (Distance to Liquidation)](#청산까지-거리-distance-to-liquidation)

---

## 청산가 (Liquidation Price)

### 공식

**기본 개념:**
```
Max Loss = Initial Margin - Maintenance Margin
```

**LONG 포지션:**
```
Liquidation Price = Entry Price - (Max Loss / Position Size)
```

**SHORT 포지션:**
```
Liquidation Price = Entry Price + (Max Loss / Position Size)
```

### 설명

- **Initial Margin**: 포지션을 열 때 필요한 초기 마진
- **Maintenance Margin**: 포지션을 유지하기 위한 최소 마진
- **Max Loss**: 청산되기 전까지 감당할 수 있는 최대 손실

### DEX별 설정값

```python
# {DEX_NAME} 설정
INITIAL_MARGIN_RATE = {DEX_SPECIFIC}  # 예: 0.1 (10%)
MAINTENANCE_MARGIN_RATE = {DEX_SPECIFIC}  # 예: 0.05 (5%)
```

### 예시

**SHORT 포지션 청산가 계산:**

```python
# 포지션 정보
Entry Price = ${DEX_SPECIFIC}  # 진입가
Position Size = {DEX_SPECIFIC} BTC
Initial Margin = ${DEX_SPECIFIC} USDT
Maintenance Margin = ${DEX_SPECIFIC} USDT

# 계산
Max Loss = Initial Margin - Maintenance Margin

# SHORT 포지션 청산가
Liquidation Price = Entry Price + (Max Loss / Position Size)

# 결과: BTC 가격이 Liquidation Price까지 상승하면 청산됨
```

---

## 미실현 손익 (Unrealized PnL)

### 공식

**LONG 포지션:**
```
Unrealized PnL = (Current Price - Entry Price) × Position Size
```

**SHORT 포지션:**
```
Unrealized PnL = (Entry Price - Current Price) × Position Size
```

### 설명

- **양수 (+)**: 수익 상태
- **음수 (-)**: 손실 상태
- **Current Price**: Mark Price 또는 Last Price 사용 ({DEX_SPECIFIC}에서 확인)

---

## 레버리지 (Leverage)

### 공식

```
Leverage = 1 / Margin Rate
```

또는

```
Leverage = Position Value / Margin Used
```

### 설명

- **Margin Rate**: 각 DEX마다 다를 수 있음
- **Position Value**: 포지션 가치 (Entry Price × Size)
- **Margin Used**: 실제 사용된 마진

### 레버리지별 Margin Rate (참고)

| 레버리지 | Margin Rate | 설명 |
|---------|-------------|------|
| 1x | 1.0 (100%) | 레버리지 없음 |
| 2x | 0.5 (50%) | 2배 레버리지 |
| 5x | 0.2 (20%) | 5배 레버리지 |
| 10x | 0.1 (10%) | 10배 레버리지 |
| 20x | 0.05 (5%) | 20배 레버리지 |
| 50x | 0.02 (2%) | 50배 레버리지 |
| 100x | 0.01 (1%) | 100배 레버리지 |

> **주의**: DEX마다 지원하는 최대 레버리지가 다를 수 있습니다.

---

## 마진 사용량 (Margin Usage)

### 공식

```
Margin Used = Position Value × Margin Rate
```

또는

```
Margin Used = (Entry Price × Position Size) × Margin Rate
```

---

## 청산까지 거리 (Distance to Liquidation)

### 공식

**LONG 포지션:**
```
Distance % = ((Current Price - Liquidation Price) / Current Price) × 100
```
- 가격이 **하락**하면 청산

**SHORT 포지션:**
```
Distance % = ((Liquidation Price - Current Price) / Current Price) × 100
```
- 가격이 **상승**하면 청산

### 설명

- **양수 (+)**: 청산가까지 여유가 있음 (안전)
- **음수 (-)**: 이미 청산가를 넘어섬 (위험)
- 퍼센트 값은 현재가 대비 가격 변동 폭을 의미

---

## PnL 퍼센트 (마진 대비)

### 공식

```
PnL % = (Unrealized PnL / Margin Used) × 100
```

### 설명

실제 투자한 마진 대비 손익 비율을 나타냅니다. 레버리지가 높을수록 PnL %가 크게 변동합니다.

---

## 주의사항

1. **Funding Fee 영향**: 실제 청산가는 누적 펀딩비로 인해 약간 달라질 수 있습니다.

2. **Mark Price vs Last Price**: 청산 계산은 Mark Price를 기준으로 하는 DEX가 많으나, 확인 필요합니다.

3. **실시간 변동**: 마진 정보는 실시간으로 변동하므로, 계산 시점에 따라 결과가 다를 수 있습니다.

4. **오차 범위**: 웹사이트 표시 값과 1-2% 차이는 정상입니다 (펀딩비, 수수료, 소수점 처리 차이).

5. **DEX별 차이**: 각 DEX마다 청산 메커니즘, 수수료 구조, 펀딩비 계산 방식이 다를 수 있으므로 공식 문서를 확인하세요.

---

## DEX별 구현 체크리스트

각 DEX 폴더에서 이 템플릿을 복사하여 다음을 확인하세요:

- [ ] Initial Margin Rate 확인
- [ ] Maintenance Margin Rate 확인
- [ ] 청산 메커니즘 검증 (Mark Price / Last Price / Index Price)
- [ ] Funding Fee 계산 방식 확인
- [ ] 최대 레버리지 제한 확인
- [ ] 청산 페널티 여부 확인
- [ ] 공식 문서 링크 추가
