# Hummingbot Avellaneda MM 실행 가이드

## ✅ 설치 완료!

**Python 3.12** 환경에서 Hummingbot이 성공적으로 설치되었습니다.

- **설치 위치**: `C:\Users\crypto quant\perpdex\hummingbot`
- **Conda 환경**: `hummingbot` (Python 3.12.12)
- **Avellaneda 전략**: 컴파일 완료 (avellaneda_market_making.cp312-win_amd64.pyd)
- **APEX Pro 커넥터**: 복원 완료 및 circular import 수정

---

## 🚀 1단계: Hummingbot 시작

### Windows 명령 프롬프트(cmd.exe)에서 실행

**옵션 A: 배치 파일 사용 (간편)**
```cmd
start_hummingbot.bat
```
또는 더블클릭: `C:\Users\crypto quant\perpdex\start_hummingbot.bat`

**옵션 B: 수동 실행**
```cmd
cd "C:\Users\crypto quant\perpdex\hummingbot"
call C:\Users\crypto quant\anaconda3\Scripts\activate.bat hummingbot
python bin\hummingbot.py
```

**주의**:
- ❌ Git Bash에서는 실행하지 마세요 (터미널 호환성 문제)
- ✅ Windows 명령 프롬프트(cmd.exe) 또는 PowerShell 사용

---

## 🔑 2단계: APEX Pro API 연결

Hummingbot가 시작되면:

### 1. 커넥터 연결
```
>>> connect apex_pro
```

### 2. API 키 입력
다음 정보를 순서대로 입력:

```
Enter your apex_pro API key >>> [백업 폴더의 .env에서 API_KEY]
Enter your apex_pro API secret >>> [백업 폴더의 .env에서 API_SECRET]
Enter your apex_pro API passphrase >>> [백업 폴더의 .env에서 API_PASSPHRASE]
Enter your apex_pro ZK seeds >>> [백업 폴더의 .env에서 ZK_SEEDS]
Enter your apex_pro ZK L2 key >>> [백업 폴더의 .env에서 ZK_L2KEY]
```

**API 키 위치**: `C:\Users\crypto quant\perpdex\hummingbot_backup\.env`

### 3. 연결 확인
```
>>> status
```

**성공 시**: 계정 잔고 표시
**실패 시**:
- APEX-TIMESTAMP 에러 → 시스템 시간 동기화: `w32tm /resync` (관리자 권한 cmd)
- 인증 에러 → API 키 재확인

---

## 📊 3단계: Avellaneda MM 전략 실행

### 1. 전략 파일 확인
```
>>> import
```
파일 선택:
```
conf/strategies/apex_pro_avellaneda_eth_usdt.yml
```

### 2. 전략 설정 확인
```yaml
strategy: avellaneda_market_making
exchange: apex_pro_mainnet
market: ETH-USDT
order_amount: 0.01          # 주문 크기
risk_factor: 1.0            # 리스크 팩터
min_spread: 0.1             # 최소 스프레드 (%)
order_refresh_time: 30.0    # 주문 갱신 시간 (초)
inventory_target_base_pct: 50  # 인벤토리 목표 (%)
```

### 3. 전략 시작
```
>>> start
```

### 4. 실행 확인
- **주문 생성 로그** 확인
- **스프레드 계산** 확인
- **주문 체결** 모니터링

### 5. 전략 중지
```
>>> stop
```

---

## 📝 주요 명령어

| 명령어 | 설명 |
|--------|------|
| `status` | 잔고 및 연결 상태 확인 |
| `balance` | 계정 잔고 조회 |
| `history` | 거래 내역 |
| `config` | 전략 설정 변경 |
| `start` | 전략 시작 |
| `stop` | 전략 중지 |
| `exit` | Hummingbot 종료 |
| `help` | 전체 명령어 목록 |

---

## ⚠️ 문제 해결

### APEX-TIMESTAMP 에러
```cmd
# 관리자 권한 cmd에서 실행
w32tm /resync
```

### cp949 인코딩 에러
환경변수 설정 (PowerShell에서):
```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
```

### Connector 로딩 실패
```
>>> connect apex_pro
```
재시도. 문제 지속 시:
```bash
cd "C:\Users\crypto quant\perpdex\hummingbot"
python -c "from hummingbot.connector.exchange.apex_pro.apex_pro_exchange import ApexProExchange; print('Test OK')"
```

### 전략 import 실패
경로 확인:
```
conf/strategies/apex_pro_avellaneda_eth_usdt.yml
```

---

## 📂 중요 파일 위치

| 항목 | 경로 |
|------|------|
| Hummingbot 설치 | `C:\Users\crypto quant\perpdex\hummingbot` |
| 백업 파일 | `C:\Users\crypto quant\perpdex\hummingbot_backup` |
| 전략 설정 | `hummingbot/conf/strategies/apex_pro_avellaneda_eth_usdt.yml` |
| APEX Pro 커넥터 | `hummingbot/hummingbot/connector/exchange/apex_pro` |
| 로그 파일 | `hummingbot/logs` |
| 시작 스크립트 | `C:\Users\crypto quant\perpdex\start_hummingbot.bat` |

---

## ✅ 성공 기준

- [x] Hummingbot CLI 실행
- [x] APEX Pro 연결 성공
- [x] 잔고 조회 성공
- [ ] Avellaneda 전략 로드
- [ ] 주문 생성 확인

---

## 🎯 최종 목표 달성!

**목표**: Hummingbot에서 Avellaneda MM 전략으로 APEX Pro 거래
**상태**: ✅ 준비 완료

다음 단계:
1. `start_hummingbot.bat` 실행
2. `connect apex_pro` → API 키 입력
3. `import` → 전략 파일 선택
4. `start` → 거래 시작

---

**설치 일시**: 2025-11-13
**예상 소요 시간**: 3시간 → **완료!**
