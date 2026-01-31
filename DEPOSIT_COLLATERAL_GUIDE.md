# Nado Testnet 담보금 입금 가이드

## 문제
주문 실행 시 "Insufficient account health" 에러가 발생합니다.

## 해결 방법: 담보금 입금

### 1. Nado Testnet Faucet

Nado testnet에 무료 테스트 토큰을 요청합니다:

```bash
# Nado testnet faucet URL
https://faucet.test.nado.xyz
```

### 2. 계정 주소

당신의 지갑 주소:
```
0x883064f137d4d65D19b1D55275b374Fb0ade026A
```

### 3. 입금 절차

1. 위 Faucet 사이트 접속
2. 지갑 주소 입력: `0x883064f137d4d65D19b1D55275b374Fb0ade026A`
3. "Request" 버튼 클릭
4. 테스트 토큰 수신 대기 (약 1-2분)

### 4. 입금 확인

입금 후 계정 상태 확인:

```bash
python3 tests/check_account_health.py
```

다음과 같은 결과가 나와야 합니다:
```
Healths: [SubaccountHealth(assets='1000', liabilities='0', health='100000'), ...]
```

### 5. Fill 메시지 테스트

담보금 입금 후:

```bash
python3 tests/test_fill_message_reception.py
```

---

## 대안: 다른 방법으로 테스트

이미 체결된 주문이 있다면, WebSocket으로 들어오는 과거 Fill 메시지를 기다리지 않고:

1. **다른 계정 사용**: 이미 자금이 있는 다른 지갑 주소 사용
2. **메인넷 전환**: 실제 자금이 있는 메인넷에서 테스트 (`NADO_MODE=MAINNET`)
3. **Nado 팀 문의**: Testnet faucet에 문의하여 대량 테스트 토큰 요청

---

## 참고

- 계정 health = (자산 / 부채) × 100000
- 주문 실행에는 최소 health > 0 필요
- 포지션 유지中也에는 충분한 health 유지 필요
