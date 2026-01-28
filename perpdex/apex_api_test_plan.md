# ApeX API 안전 테스트 계획 (간소화 버전)

## 📋 API 구조 분석

### 인증 방식
```yaml
계좌_조회용_필수_항목 (3개):
  - APEX_API_KEY: "API Key"
  - APEX_API_SECRET: "API Secret"
  - APEX_API_PASSPHRASE: "API Passphrase"

주문_생성용_추가_항목 (현재 불필요):
  - APEX_ZK_SEEDS: "ZK Seeds"
  - APEX_ZK_L2KEY: "L2 Key"

signature_method:
  - HMAC-SHA256
  - timestamp + httpMethod + requestPath
  - Base64 encoding
```

### API 엔드포인트
```yaml
testnet: "https://omni-test.pro.apex.exchange"
mainnet: "https://omni.pro.apex.exchange"

network_ids:
  - NETWORKID_OMNI_TEST_BNB (테스트넷)
  - NETWORKID_OMNI_MAIN_ARB (메인넷)
```

### 계좌 조회 API
```python
# Public API (인증 불필요)
- configs_v3()          # 시스템 설정
- klines_v3()          # 캔들 데이터
- depth_v3()           # 호가창
- ticker_v3()          # 시세

# Private API (인증 필요 - 3개 항목만)
- get_account_v3()              # 계좌 정보
- get_account_balance_v3()      # 잔액 조회
- open_orders_v3()              # 미체결 주문
- history_orders_v3()           # 주문 내역
```

---

## 🔐 API Key 안전 관리 전략 (환경 변수 방식)

### 구현 방법

**장점**:
- Git에 절대 포함되지 않음
- 코드와 완전 분리
- 표준 관행
- **3개 항목만 관리**

---

## 🚀 실행 계획 (10분 완성)

### Phase 1: 환경 설정 (3분)

```bash
# 1. 디렉토리 생성
cd "C:\Users\crypto quant\perpdex farm"
mkdir apex_test
cd apex_test

# 2. Python 가상환경 생성
python -m venv venv
venv\Scripts\activate

# 3. 패키지 설치
pip install apexomni python-dotenv

# 4. .gitignore 생성
echo .env > .gitignore
echo venv/ >> .gitignore
echo *.pyc >> .gitignore
echo __pycache__/ >> .gitignore
```

---

### Phase 2: .env 파일 작성 (3분)

#### 2-1. .env.example 템플릿 파일 생성 (Git 커밋용)

먼저 예제 파일을 만듭니다 (이 파일은 Git에 커밋해도 안전):

```bash
# .env.example 파일 생성 (템플릿)
notepad .env.example
```

**.env.example 파일 내용**:
```env
# ApeX API 자격 증명 (계좌 조회용)
# https://omni.apex.exchange/keyManagement 에서 발급

APEX_API_KEY=your-api-key-here
APEX_API_SECRET=your-api-secret-here
APEX_API_PASSPHRASE=your-passphrase-here

# 주문 생성용 (현재 불필요 - 주석 처리)
# APEX_ZK_SEEDS=
# APEX_ZK_L2KEY=
```

#### 2-2. API Key 발급 받기

1. **ApeX 웹사이트 접속**
   - 테스트넷: https://omni-test.apex.exchange/keyManagement
   - 메인넷: https://omni.apex.exchange/keyManagement

2. **API Key 생성 클릭**
   - "Generate API" 버튼 클릭
   - Passphrase 입력 (본인이 기억할 수 있는 비밀번호)
   - 권한 설정: "Read Only" 체크 (안전)

3. **3개 값 복사**
   ```
   API Key:        f6c1e736-fa6b-01df-2822-b9359b3918ae
   API Secret:     sAVchdqy_n9zY7TOIDsqkyg0we3uF0_gGbvyIoob
   API Passphrase: Ri08mFrOt2Uaiym
   ```
   ⚠️ **주의**: 이 값들은 한 번만 표시됩니다. 반드시 복사하세요!

#### 2-3. 실제 .env 파일 생성 (절대 Git에 커밋 안 함)

```bash
# .env 파일 생성 (실제 값 입력용)
notepad .env
```

**.env 파일 내용** (실제 값으로 교체):

```env
# ApeX API 자격 증명 - 절대 공유하지 마세요!
APEX_API_KEY=f6c1e736-fa6b-01df-2822-b9359b3918ae
APEX_API_SECRET=sAVchdqy_n9zY7TOIDsqkyg0we3uF0_gGbvyIoob
APEX_API_PASSPHRASE=Ri08mFrOt2Uaiym
```

#### 2-4. 값 입력 형식 (중요!)

```env
# ✅ 올바른 형식 (띄어쓰기 없음, 따옴표 없음)
APEX_API_KEY=f6c1e736-fa6b-01df-2822-b9359b3918ae

# ❌ 잘못된 형식들
APEX_API_KEY = f6c1e736-fa6b-01df-2822-b9359b3918ae  # = 앞뒤 공백 X
APEX_API_KEY="f6c1e736-fa6b-01df-2822-b9359b3918ae"  # 따옴표 X
APEX_API_KEY=f6c1e736-fa6b-01df-2822-b9359b3918ae   # 뒤에 공백 X
```

#### 2-5. 검증

```bash
# .env 파일이 제대로 만들어졌는지 확인
type .env

# 출력 예시:
# APEX_API_KEY=f6c1e736-fa6b-01df-2822-b9359b3918ae
# APEX_API_SECRET=sAVchdqy_n9zY7TOIDsqkyg0we3uF0_gGbvyIoob
# APEX_API_PASSPHRASE=Ri08mFrOt2Uaiym
```

#### 2-6. 보안 확인

```bash
# .gitignore가 제대로 설정되었는지 확인
git status

# .env가 "Untracked files"에 보이면 안 됨!
# .gitignore 덕분에 Git이 무시해야 함
```

**완료 체크리스트**:
```
□ .env.example 파일 생성 완료
□ API Key 3개 발급 완료
□ .env 파일에 실제 값 입력 완료
□ 띄어쓰기, 따옴표 없이 올바른 형식으로 입력
□ git status로 .env가 무시되는지 확인
```

---

### Phase 3: 테스트 스크립트 작성 (2분)

**simple_test.py** 생성:

```python
# simple_test.py
import os
from dotenv import load_dotenv
from apexomni.http_private_v3 import HttpPrivate_v3
from apexomni.http_public import HttpPublic
from apexomni.constants import APEX_OMNI_HTTP_TEST, NETWORKID_OMNI_TEST_BNB

# 환경 변수 로드
load_dotenv()

print("=" * 60)
print("ApeX API 연결 테스트")
print("=" * 60)

# 1. Public API 테스트 (인증 불필요)
print("\n[1] Public API 테스트 (인증 불필요)...")
try:
    public_client = HttpPublic(APEX_OMNI_HTTP_TEST)
    configs = public_client.configs_v3()

    if 'data' in configs:
        symbols_count = len(configs['data'].get('perpetualContract', []))
        print(f"✅ Public API 성공")
        print(f"   - 거래 가능 심볼: {symbols_count}개")
    else:
        print(f"⚠️  Public API 응답: {configs}")

except Exception as e:
    print(f"❌ Public API 실패: {e}")

# 2. Private API 테스트 (3개 항목 필요)
print("\n[2] Private API 테스트 (계좌 조회)...")

# .env에서 3개 로드
key = os.getenv('APEX_API_KEY')
secret = os.getenv('APEX_API_SECRET')
passphrase = os.getenv('APEX_API_PASSPHRASE')

# 검증
if not all([key, secret, passphrase]):
    print("❌ .env 파일에 다음 3개 항목이 필요합니다:")
    print("   - APEX_API_KEY")
    print("   - APEX_API_SECRET")
    print("   - APEX_API_PASSPHRASE")
    exit(1)

try:
    # 클라이언트 초기화 (ZK 없이 - 계좌 조회만)
    private_client = HttpPrivate_v3(
        APEX_OMNI_HTTP_TEST,
        network_id=NETWORKID_OMNI_TEST_BNB,
        api_key_credentials={
            'key': key,
            'secret': secret,
            'passphrase': passphrase
        }
        # zk_seeds, zk_l2Key는 생략 (주문 생성 시에만 필요)
    )

    # 계좌 정보 조회
    print("   > 계좌 정보 조회 중...")
    account = private_client.get_account_v3()

    if 'data' in account:
        account_data = account['data']
        print(f"✅ 계좌 조회 성공")
        print(f"   - Account ID: {account_data.get('id', 'N/A')}")
        print(f"   - Ethereum Address: {account_data.get('ethereumAddress', 'N/A')[:10]}...")

        # 잔액 조회
        print("   > 잔액 조회 중...")
        balance = private_client.get_account_balance_v3()

        if 'data' in balance:
            balance_data = balance['data']
            print(f"✅ 잔액 조회 성공")
            print(f"   - Total Equity: {balance_data.get('totalEquity', '0')} USDT")
            print(f"   - Available Balance: {balance_data.get('availableBalance', '0')} USDT")
        else:
            print(f"⚠️  잔액 응답: {balance}")
    else:
        print(f"⚠️  계좌 응답: {account}")

except Exception as e:
    print(f"❌ Private API 실패")
    print(f"   에러 타입: {type(e).__name__}")
    print(f"   에러 내용: {str(e)}")

    # 일반적인 에러 해결 방법
    if "401" in str(e) or "Unauthorized" in str(e):
        print("\n💡 해결 방법:")
        print("   1. .env 파일의 API Key가 정확한지 확인")
        print("   2. Passphrase가 올바른지 확인")
        print("   3. API Key가 활성화되어 있는지 확인")
    elif "403" in str(e) or "Forbidden" in str(e):
        print("\n💡 해결 방법:")
        print("   1. API Key에 계좌 조회 권한이 있는지 확인")
        print("   2. IP 화이트리스트 설정 확인")

print("\n" + "=" * 60)
print("테스트 완료")
print("=" * 60)
```

---

### Phase 4: 실행 (1분)

```bash
# 가상환경 활성화 (아직 안 했다면)
venv\Scripts\activate

# 테스트 실행
python simple_test.py
```

---

## 📊 예상 결과

### ✅ 성공 시

```
============================================================
ApeX API 연결 테스트
============================================================

[1] Public API 테스트 (인증 불필요)...
✅ Public API 성공
   - 거래 가능 심볼: 45개

[2] Private API 테스트 (계좌 조회)...
   > 계좌 정보 조회 중...
✅ 계좌 조회 성공
   - Account ID: 123456789
   - Ethereum Address: 0xABC12345...
   > 잔액 조회 중...
✅ 잔액 조회 성공
   - Total Equity: 1000.00 USDT
   - Available Balance: 950.00 USDT

============================================================
테스트 완료
============================================================
```

### ❌ 실패 시 (API Key 오류)

```
[2] Private API 테스트 (계좌 조회)...
   > 계좌 정보 조회 중...
❌ Private API 실패
   에러 타입: HTTPError
   에러 내용: 401 Unauthorized

💡 해결 방법:
   1. .env 파일의 API Key가 정확한지 확인
   2. Passphrase가 올바른지 확인
   3. API Key가 활성화되어 있는지 확인
```

---

## 🔒 보안 체크리스트

### 실행 전
```
□ .env 파일 생성
□ .gitignore에 .env 추가
□ API Key 3개 항목 모두 입력
```

### 실행 후
```
□ git status 실행 → .env가 untracked인지 확인
□ 터미널 히스토리에 API Key 노출 여부 확인
□ 스크린샷 찍을 때 .env 파일 숨김
```

### Git 커밋 전 필수 확인
```bash
# .env가 추적되지 않는지 확인
git status

# 출력에 .env가 없어야 함
# Untracked files에도 없어야 함 (.gitignore 적용됨)
```

---

## 🎯 다음 단계 (테스트 성공 후)

### 1단계: 시세 데이터 조회 테스트

```python
# price_check.py
# 계좌 조회 성공 후 시세 확인 테스트

# BTC 현재가 조회
ticker = private_client.ticker_v3(symbol="BTC-USDT")
print(f"BTC 현재가: {ticker}")

# 호가창 조회
depth = private_client.depth_v3(symbol="BTC-USDT")
print(f"호가창: {depth}")

# 미체결 주문 조회
open_orders = private_client.open_orders_v3()
print(f"미체결 주문: {open_orders}")
```

### 2단계: 주문 관련 기능 (ZK 필요)

이 단계에서는 추가로 필요:
```env
APEX_ZK_SEEDS=your-zk-seeds
APEX_ZK_L2KEY=your-l2key
```

---

## 🛡️ apikey_mgt.md 원칙 준수

1. **Private Key는 사용을 제어한다**
   - ✅ 환경 변수로 접근 제어
   - ✅ Git에서 완전 격리
   - ✅ 읽기 전용 작업만 수행

2. **요청은 검증된다**
   - ✅ HMAC-SHA256 서명
   - ✅ Timestamp 기반 검증
   - ✅ Passphrase 추가 검증

3. **보안은 행위의 제어다**
   - ✅ 계좌 조회만 가능 (ZK 없음)
   - ✅ 주문 생성은 별도 검증 필요

---

## 📝 핵심 요약

### 필요한 것
```env
APEX_API_KEY=xxx
APEX_API_SECRET=yyy
APEX_API_PASSPHRASE=zzz
```

### 불필요한 것 (지금)
```env
APEX_ZK_SEEDS=  (주문 생성 시에만)
APEX_ZK_L2KEY=  (주문 생성 시에만)
```

### 실행 순서
1. `venv` 생성 및 패키지 설치
2. `.env` 파일에 3개 항목 입력
3. `.gitignore` 설정
4. `python simple_test.py` 실행
5. ✅ 계좌 조회 성공 확인

### 소요 시간
- 환경 설정: 3분
- .env 작성: 1분
- 스크립트 작성: 2분
- 실행 및 확인: 1분
- **총 7분**

---

## ❓ FAQ

**Q1: 왜 3개가 필요한가?**
A: ApeX가 OKX 보안 모델을 채택했기 때문. Passphrase는 HTTP 헤더에 필수입니다.

**Q2: 2개로는 불가능한가?**
A: 불가능합니다. SDK가 3개를 요구합니다.

**Q3: ZK Seeds는 언제 필요한가?**
A: 주문 생성, 출금, 전송 등 "쓰기" 작업 시에만 필요. 계좌 조회는 불필요.

**Q4: Testnet vs Mainnet?**
A: 테스트는 `APEX_OMNI_HTTP_TEST` 사용. 실제 거래는 `APEX_OMNI_HTTP_MAIN`.

**Q5: API Key 권한 설정은?**
A: https://omni.apex.exchange/keyManagement 에서 생성 시 "Read Only" 체크하면 안전.
