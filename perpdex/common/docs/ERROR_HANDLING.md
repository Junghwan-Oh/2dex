# 에러 처리 가이드 (공통)

Perpetual DEX API 사용 시 발생할 수 있는 공통 에러와 해결 방법을 정리한 문서입니다.

> **사용 방법**: 이 문서는 범용 에러 처리 패턴을 다룹니다. DEX별 구체적인 에러 코드와 메시지는 각 DEX 폴더의 문서를 참고하세요.

## 목차
- [인증 관련 에러](#인증-관련-에러)
- [API 메서드 에러](#api-메서드-에러)
- [데이터 파싱 에러](#데이터-파싱-에러)
- [네트워크 에러](#네트워크-에러)
- [계산 에러](#계산-에러)
- [에러 처리 패턴](#에러-처리-패턴)

---

## 인증 관련 에러

### 에러 1: API Key 누락

**에러 메시지:**
```
ValueError: .env 파일에 API Key가 필요합니다
```

**원인:**
- `.env` 파일이 없거나 필수 항목이 누락됨

**해결 방법:**

1. 프로젝트 루트에 `.env` 파일 생성:
```bash
# DEX별 API Key 명명 규칙 확인
# 예시:
# APEX_API_KEY=your-api-key-here
# APEX_API_SECRET=your-api-secret-here
# APEX_API_PASSPHRASE=your-passphrase-here
```

2. 환경 변수 로드 확인:
```python
from dotenv import load_dotenv
import os

load_dotenv()

key = os.getenv('YOUR_DEX_API_KEY')
if not key:
    print("API Key가 로드되지 않았습니다")
```

---

### 에러 2: 401 Unauthorized

**에러 메시지:**
```
401 Unauthorized
```

**원인:**
- API Key, Secret, Passphrase가 잘못됨
- 메인넷/테스트넷 환경 불일치
- API Key가 비활성화됨

**해결 방법:**

1. **자격 증명 확인:**
```python
# .env 파일 내용 확인
print(f"API Key 길이: {len(os.getenv('YOUR_DEX_API_KEY', ''))}")
print(f"API Secret 길이: {len(os.getenv('YOUR_DEX_API_SECRET', ''))}")
```

2. **환경 일치 확인:**
- 메인넷 API Key는 메인넷에서만 작동
- 테스트넷 API Key는 테스트넷에서만 작동

3. **API Key 상태 확인:**
- DEX 웹사이트 로그인
- API Management에서 Key 상태 확인
- 필요 시 새 Key 발급

---

### 에러 3: 403 Forbidden

**에러 메시지:**
```
403 Forbidden
```

**원인:**
- API Key에 권한이 없음
- IP 화이트리스트 설정 문제

**해결 방법:**

1. **권한 확인:**
- API Key 생성 시 "Read" 권한 활성화 확인
- 주문 생성이 필요하면 "Trade" 권한 추가

2. **IP 화이트리스트 확인:**
- DEX 웹사이트에서 IP 제한 설정 확인
- 현재 IP 주소를 화이트리스트에 추가

```bash
# 현재 공인 IP 확인
curl ifconfig.me
```

---

## API 메서드 에러

### 에러 4: AttributeError - 메서드 없음

**에러 메시지:**
```
AttributeError: 'Client' object has no attribute 'method_name'
```

**원인:**
- 존재하지 않는 메서드 호출
- 메서드 이름 오타

**해결 방법:**

1. **사용 가능한 메서드 확인:**
```python
# 모든 메서드 목록 확인
methods = [m for m in dir(client) if not m.startswith('_')]
print("사용 가능한 메서드:")
for method in methods:
    print(f"  - {method}")
```

2. **공식 문서 참고:**
- 각 DEX의 공식 SDK 문서 확인
- 올바른 메서드 이름 및 파라미터 확인

<!--
ApeX 예시 (주석 처리):
| 클래스 | 메서드 | 설명 |
|--------|--------|------|
| HttpPublic | `ticker_v3(symbol)` | 단일 심볼 티커 조회 |
| HttpPrivate_v3 | `get_account_v3()` | 계좌 정보 조회 |
-->

---

## 데이터 파싱 에러

### 에러 5: 'list' object has no attribute 'get'

**에러 메시지:**
```
AttributeError: 'list' object has no attribute 'get'
```

**원인:**
- API 응답 구조를 잘못 이해함
- 응답이 리스트인데 딕셔너리로 접근

**해결 방법:**

```python
# ❌ 틀린 예
ticker_data = client.get_ticker(symbol='BTC-USDT')
ticker = ticker_data['data']  # 이것이 리스트일 수 있음
price = ticker.get('lastPrice')  # 에러 발생

# ✅ 올바른 예
ticker_data = client.get_ticker(symbol='BTC-USDT')
if ticker_data and 'data' in ticker_data:
    data = ticker_data['data']
    # data가 리스트인지 딕셔너리인지 확인
    if isinstance(data, list) and len(data) > 0:
        ticker = data[0]  # 첫 번째 요소
        price = ticker.get('lastPrice')
    elif isinstance(data, dict):
        price = data.get('lastPrice')
```

**일반적인 응답 구조 확인:**

```python
import json

# 전체 응답 구조 확인
response = client.get_ticker('BTC-USDT')
print(json.dumps(response, indent=2, ensure_ascii=False))
```

---

### 에러 6: KeyError - 키 없음

**에러 메시지:**
```
KeyError: 'lastPrice'
```

**원인:**
- 예상한 키가 응답에 없음
- API 응답 구조 변경
- 빈 응답

**해결 방법:**

```python
# ❌ 틀린 예
price = ticker['lastPrice']  # 키가 없으면 에러

# ✅ 올바른 예 (Option 1: .get() 사용)
price = ticker.get('lastPrice', 0)  # 기본값 0

# ✅ 올바른 예 (Option 2: 키 존재 확인)
if 'lastPrice' in ticker:
    price = ticker['lastPrice']
else:
    print("[WARNING] lastPrice 키 없음")
    price = 0
```

---

### 에러 7: TypeError - float() 변환 실패

**에러 메시지:**
```
TypeError: float() argument must be a string or a number, not 'NoneType'
```

**원인:**
- None 값을 float()로 변환 시도
- API 응답에서 값이 누락됨

**해결 방법:**

```python
# ❌ 틀린 예
size = float(position.get('size'))  # None이면 에러

# ✅ 올바른 예
size = float(position.get('size', '0'))  # 기본값 '0'

# ✅ 더 안전한 예
def safe_float(value, default=0.0):
    """안전한 float 변환"""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default

size = safe_float(position.get('size'))
```

---

## 네트워크 에러

### 에러 8: Connection Error

**에러 메시지:**
```
ConnectionError: Failed to establish a new connection
```

**원인:**
- 네트워크 연결 문제
- API 서버 다운타임
- 방화벽/프록시 차단

**해결 방법:**

1. **네트워크 확인:**
```bash
# API 서버 연결 테스트
ping api.dex.com  # DEX별 API 주소 사용
curl https://api.dex.com
```

2. **재시도 로직 구현:**
```python
import time

def retry_api_call(func, max_retries=3, delay=1):
    """재시도 로직"""
    for attempt in range(max_retries):
        try:
            return func()
        except ConnectionError as e:
            if attempt < max_retries - 1:
                print(f"[RETRY] {attempt + 1}번째 재시도 중...")
                time.sleep(delay * (attempt + 1))  # 지수 백오프
            else:
                raise e

# 사용 예시
account = retry_api_call(lambda: client.get_account())
```

---

### 에러 9: Timeout Error

**에러 메시지:**
```
TimeoutError: Request timed out
```

**원인:**
- API 서버 응답 지연
- 네트워크 속도 느림

**해결 방법:**

```python
import requests

# Timeout 설정 (연결 5초, 읽기 10초)
session = requests.Session()
session.timeout = (5, 10)

# 또는 개별 요청에 timeout 설정
response = requests.get(url, timeout=10)
```

---

## 계산 에러

### 에러 10: 청산가 계산 오류

**증상:**
- 계산된 청산가가 웹사이트와 크게 다름 (>5% 차이)

**원인:**
- 잘못된 공식 사용
- Funding Fee 미고려
- 마진 정보 오류

**해결 방법:**

1. **올바른 공식 사용:**
```python
# ✅ 올바른 공식
max_loss = initial_margin - maintenance_margin

if side == 'SHORT':
    liquidation_price = entry_price + (max_loss / size)
elif side == 'LONG':
    liquidation_price = entry_price - (max_loss / size)

# ❌ 잘못된 공식 (사용하지 마세요)
# maintenance_rate = margin_rate * 0.5
# liquidation_price = entry_price * (1 + margin_rate - maintenance_rate)
```

2. **마진 정보 확인:**
```python
balance_info = client.get_account_balance()
data = balance_info['data']

initial_margin = float(data.get('initialMargin', 0))
maintenance_margin = float(data.get('maintenanceMargin', 0))

print(f"Initial Margin: {initial_margin}")
print(f"Maintenance Margin: {maintenance_margin}")
```

3. **허용 오차:**
- 웹사이트와 1-2% 차이는 정상 (펀딩비, 타이밍 차이)
- 5% 이상 차이는 공식 오류 가능성 높음

---

### 에러 11: Division by Zero

**에러 메시지:**
```
ZeroDivisionError: division by zero
```

**원인:**
- 포지션 크기가 0
- 마진 비율이 0

**해결 방법:**

```python
# ❌ 틀린 예
liquidation_price = entry_price + (max_loss / size)  # size=0이면 에러

# ✅ 올바른 예
def calculate_liquidation_price_safe(side, entry_price, size, initial_margin, maintenance_margin):
    """안전한 청산가 계산"""
    if size <= 0:
        return 0

    max_loss = initial_margin - maintenance_margin
    if max_loss <= 0:
        return 0

    if side == 'LONG':
        return entry_price - (max_loss / size)
    elif side == 'SHORT':
        return entry_price + (max_loss / size)

    return 0
```

---

## 에러 처리 패턴

### 패턴 1: Try-Except-Else-Finally

```python
try:
    # API 호출
    account = client.get_account()

    # 응답 검증
    if not account:
        raise ValueError("계좌 조회 실패 - 빈 응답")

except ValueError as e:
    # 특정 에러 처리
    print(f"[ERROR] 값 오류: {e}")

except ConnectionError as e:
    # 네트워크 에러
    print(f"[ERROR] 연결 실패: {e}")

except Exception as e:
    # 기타 모든 에러
    print(f"[ERROR] 알 수 없는 오류: {e}")
    import traceback
    traceback.print_exc()

else:
    # 에러 없을 때만 실행
    print("[SUCCESS] 계좌 조회 성공")

finally:
    # 항상 실행 (리소스 정리)
    print("[INFO] API 호출 완료")
```

---

### 패턴 2: 안전한 API 호출 래퍼

```python
def safe_api_call(func, error_msg="API 호출 실패", default=None):
    """안전한 API 호출 래퍼"""
    try:
        result = func()
        if not result:
            print(f"[WARNING] {error_msg} - 빈 응답")
            return default
        return result

    except Exception as e:
        print(f"[ERROR] {error_msg}: {e}")
        return default

# 사용 예시
account = safe_api_call(
    func=lambda: client.get_account(),
    error_msg="계좌 조회 실패",
    default={}
)

if account:
    # 정상 처리
    pass
```

---

### 패턴 3: 데이터 검증 데코레이터

```python
def validate_response(required_keys):
    """API 응답 검증 데코레이터"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            if not result:
                print(f"[WARNING] {func.__name__} - 빈 응답")
                return None

            # 필수 키 검증
            for key in required_keys:
                if key not in result:
                    print(f"[WARNING] {func.__name__} - 필수 키 누락: {key}")
                    return None

            return result
        return wrapper
    return decorator

# 사용 예시
@validate_response(['id', 'positions', 'balance'])
def get_account_validated():
    return client.get_account()

account = get_account_validated()
```

---

### 패턴 4: 로깅 기반 에러 추적

```python
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('dex_api.log'),  # 파일 저장
        logging.StreamHandler()  # 콘솔 출력
    ]
)

logger = logging.getLogger(__name__)

# API 호출 시 로깅
try:
    logger.info("계좌 정보 조회 시작")
    account = client.get_account()
    logger.info(f"계좌 조회 성공: {account.get('id')}")

except Exception as e:
    logger.error(f"계좌 조회 실패: {e}", exc_info=True)
```

---

## 디버깅 팁

### 1. 응답 구조 확인

```python
import json

# 전체 응답 구조 확인
account = client.get_account()
print(json.dumps(account, indent=2, ensure_ascii=False))
```

### 2. 단계별 디버깅

```python
# 1단계: API 호출
print("[1] API 호출 중...")
account = client.get_account()

# 2단계: 응답 확인
print(f"[2] 응답 타입: {type(account)}")
print(f"[2] 응답 있음: {account is not None}")

# 3단계: 키 확인
if account:
    print(f"[3] 응답 키: {account.keys()}")

# 4단계: 데이터 추출
if account and 'positions' in account:
    positions = account['positions']
    print(f"[4] 포지션 개수: {len(positions)}")
```

### 3. 타입 검증

```python
def validate_type(value, expected_type, field_name):
    """타입 검증"""
    if not isinstance(value, expected_type):
        print(f"[WARNING] {field_name} 타입 오류")
        print(f"  예상: {expected_type}")
        print(f"  실제: {type(value)}")
        return False
    return True

# 사용 예시
positions = account.get('positions', [])
if validate_type(positions, list, 'positions'):
    # 정상 처리
    pass
```

---

## 문제 해결 체크리스트

API 문제 발생 시 다음 순서로 확인:

- [ ] 1. **환경 변수**: `.env` 파일 존재 및 내용 확인
- [ ] 2. **인증 정보**: Key, Secret, Passphrase 정확성
- [ ] 3. **환경 일치**: 메인넷/테스트넷 환경 일치 여부
- [ ] 4. **네트워크**: 인터넷 연결 및 API 서버 상태
- [ ] 5. **메서드 이름**: 올바른 메서드 사용 여부
- [ ] 6. **응답 구조**: API 응답 구조 이해 및 파싱
- [ ] 7. **타입 변환**: 문자열 → 숫자 변환 안전성
- [ ] 8. **에러 로그**: 스택 트레이스 확인
- [ ] 9. **공식 문서**: DEX 공식 문서 참고
- [ ] 10. **라이브러리 버전**: SDK 라이브러리 최신 버전 확인

---

## DEX별 추가 사항

각 DEX의 구체적인 에러 코드와 메시지는 해당 DEX 폴더의 문서를 참고하세요:

- ApeX: `apex/docs/ERROR_HANDLING.md`
- Hyperliquid: `hyperliquid/docs/ERROR_HANDLING.md`
- dYdX: `dydx/docs/ERROR_HANDLING.md`

---

**Template Version:** 1.0
**Last Updated:** 2025-01-23
