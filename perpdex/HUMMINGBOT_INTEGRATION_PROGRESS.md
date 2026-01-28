# Hummingbot Apex Pro Connector - 통합 진행 상황

**작성일**: 2025-11-12
**목표**: Hummingbot에 Apex Pro 커넥터 통합 (기존 apex 코드 재사용)
**전략**: Option 3 - Hybrid Approach (최소 코드로 기존 apex 재사용)

---

## 📊 현재 상태 (Current Status)

### ✅ 완료된 작업 (Completed)

1. **Phase 1: 기본 설정**
   - [x] Apex 패키지 구조 생성 (`setup.py`)
   - [x] Apex 패키지 설치 (`pip install -e apex/`)
   - [x] Hummingbot 저장소 클론
   - [x] Visual C++ Build Tools 다운로드
   - [x] Visual C++ Build Tools 설치 완료
   - [x] Cython 설치
   - [x] 통합 가이드 문서 작성 (`HUMMINGBOT_INTEGRATION_GUIDE.md`)

### ⚠️ 진행 중 (In Progress)

2. **Hummingbot 설치 - 터미널 재시작 필요**
   - Build Tools 설치 완료했으나 `cl.exe`가 PATH에 없음
   - **해결책**: 터미널 재시작 후 재설치 필요

### ⏳ 대기 중 (Pending)

3. **Phase 2: Connector 구조 생성**
   - apex_pro 디렉토리 생성
   - 5개 핵심 파일 작성 (~550 lines)

4. **Phase 3-6: 구현 및 테스트**
   - Connector 로직 구현
   - Avellaneda 전략 연동
   - 실전 테스트

---

## 🗂️ 프로젝트 구조 (Project Structure)

```
C:\Users\crypto quant\perpdex farm\
├── apex/                              # ✅ Your trading bot (installed)
│   ├── setup.py                       # ✅ Created
│   ├── __init__.py                    # ✅ Updated
│   ├── avellaneda_client.py           # ✅ Working
│   ├── lib/
│   ├── common/
│   ├── strategies/
│   └── HUMMINGBOT_INTEGRATION_GUIDE.md  # ✅ Created
│
├── hummingbot/                        # ✅ Cloned
│   ├── hummingbot/
│   │   └── connector/
│   │       └── exchange/
│   │           ├── binance/           # Reference
│   │           ├── bybit/             # Reference
│   │           └── apex_pro/          # ⏳ TO CREATE
│   │               ├── __init__.py
│   │               ├── apex_pro_exchange.py
│   │               ├── apex_pro_api_order_book_data_source.py
│   │               ├── apex_pro_user_stream_tracker.py
│   │               ├── apex_pro_auth.py
│   │               └── apex_pro_utils.py
│   └── hummingbot_install.log         # Installation log
│
├── vs_BuildTools.exe                  # ✅ Downloaded
└── HUMMINGBOT_INTEGRATION_PROGRESS.md # ✅ This file
```

---

## 🔧 터미널 재시작 후 작업 순서 (Steps After Terminal Restart)

### Step 1: Hummingbot 재설치 (5-10분)

```bash
# 1. 새 터미널 열기
# 2. 작업 디렉토리로 이동
cd "/c/Users/crypto quant/perpdex farm/hummingbot"

# 3. Hummingbot 설치 (이번엔 성공해야 함)
pip install -e .

# 4. 설치 확인
python -c "import hummingbot; print('✅ Hummingbot installed successfully!')"
```

**예상 시간**: 5-10분 (C++ 컴파일 포함)

### Step 2: Apex Import 테스트

```bash
# Apex 임포트 테스트 스크립트 실행
cd "/c/Users/crypto quant/perpdex farm/apex"
cat > test_imports.py << 'EOF'
import sys
from pathlib import Path

# Add apex to path
APEX_DIR = Path(r"C:\Users\crypto quant\perpdex farm\apex")
sys.path.insert(0, str(APEX_DIR))

print("Testing apex imports...")
try:
    from avellaneda_client import AvellanedaApexClient, AvellanedaParameters
    print("✅ SUCCESS: Apex imports work!")
    print(f"  - AvellanedaApexClient: {AvellanedaApexClient}")
    print(f"  - AvellanedaParameters: {AvellanedaParameters}")
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
EOF

python test_imports.py
```

### Step 3: Connector 생성 시작

```bash
# Claude Code에게 요청:
# "Phase 2 시작 - apex_pro connector 구조 생성해줘"
```

---

## 📝 Import 이슈 해결 방법 (Import Workaround)

### 문제
Apex 코드가 `from apex.lib.apex_client import ApexClient` 형태로 임포트하는데,
패키지 구조 때문에 일반 설치가 안 됨.

### 해결책: Runtime sys.path Injection

모든 connector 파일에 다음 코드 추가:

```python
# apex_pro_exchange.py (and other connector files)
import sys
from pathlib import Path

# Add apex to Python path
APEX_DIR = Path(r"C:\Users\crypto quant\perpdex farm\apex")
if str(APEX_DIR) not in sys.path:
    sys.path.insert(0, str(APEX_DIR))

# Now apex imports work (without "apex." prefix)
from avellaneda_client import AvellanedaApexClient
from lib.apex_client import ApexClient
from common.config import ApexConfig
```

**중요**: 다른 환경에서 실행하려면 `APEX_DIR` 경로를 환경 변수나 설정 파일로 변경 가능.

---

## 🎯 다음 단계 상세 계획 (Detailed Next Steps)

### Phase 2: Connector 디렉토리 구조 생성 (30분)

**작업 1: 디렉토리 생성**
```bash
mkdir -p "/c/Users/crypto quant/perpdex farm/hummingbot/hummingbot/connector/exchange/apex_pro"
```

**작업 2: 파일 생성 목록**
1. `__init__.py` (~30 lines)
2. `apex_pro_utils.py` (~50 lines)
3. `apex_pro_auth.py` (~50 lines)
4. `apex_pro_user_stream_tracker.py` (~100 lines)
5. `apex_pro_api_order_book_data_source.py` (~150 lines)
6. `apex_pro_exchange.py` (~250 lines) - **핵심 파일**

**총 예상 코드**: ~630 lines

### Phase 3: apex_pro_exchange.py 구현 (1-2시간)

**핵심 로직**:
```python
class ApexProExchange(ExchangeBase):
    def __init__(self, ...):
        # ✅ YOUR EXISTING CLIENT
        self.apex_client = AvellanedaApexClient(...)

    def buy(self, trading_pair, amount, order_type, price):
        # ✅ DELEGATES TO YOUR CODE
        return self.apex_client._place_limit_order(...)

    def get_order_book(self, trading_pair):
        # ✅ USES YOUR WEBSOCKET
        return self.apex_client.get_orderbook_snapshot()
```

**특징**:
- Thin wrapper (실제 로직은 apex 코드 재사용)
- Native TP/SL 지원 (당신의 혁신!)
- WebSocket 실시간 데이터

### Phase 4: Configuration (30분)

**파일 생성**:
```yaml
# hummingbot/conf/connectors/apex_pro.yml
apex_pro_api_key: ""
apex_pro_api_secret: ""
apex_pro_api_passphrase: ""
apex_pro_zk_seeds: ""
apex_pro_zk_l2key: ""

# 🌟 YOUR INNOVATIONS
apex_pro_use_native_tpsl: true
apex_pro_default_tp_pct: 0.003
apex_pro_default_sl_pct: 0.003
apex_pro_dynamic_tpsl: true
```

### Phase 5: 테스트 (1시간)

```bash
# 1. Hummingbot 실행
cd "/c/Users/crypto quant/perpdex farm/hummingbot"
./bin/hummingbot.py

# 2. Connector 테스트
connect apex_pro

# 3. Avellaneda 전략 실행
create avellaneda_market_making

# 4. 설정
exchange: apex_pro
market: BTC-USDT
order_amount: 0.001
```

---

## 🚨 알려진 이슈 및 해결책 (Known Issues)

### Issue 1: Hummingbot Build 실패
**증상**: `error: Microsoft Visual C++ 14.0 or greater is required`

**해결**:
1. ✅ Build Tools 설치 완료
2. ⚠️ 터미널 재시작 필요
3. 재설치: `pip install -e hummingbot/`

### Issue 2: Apex Import 실패
**증상**: `ModuleNotFoundError: No module named 'apex'`

**해결**: Connector 파일에 sys.path 추가 (위 참조)

### Issue 3: PyPI 패키지 충돌
**증상**: Hummingbot과 Apex 의존성 충돌

**해결**:
```bash
# 가상 환경 생성 (옵션)
python -m venv venv_hummingbot
source venv_hummingbot/bin/activate  # Linux/Mac
venv_hummingbot\Scripts\activate     # Windows

# 패키지 재설치
pip install -e apex/
pip install -e hummingbot/
```

---

## 📚 참고 자료 (References)

### 생성된 문서
1. **HUMMINGBOT_INTEGRATION_GUIDE.md** - Import 해결 방법 상세
2. **apex/setup.py** - Apex 패키지 설정
3. **apex/__init__.py** - Apex 패키지 진입점

### Hummingbot 레퍼런스
- Binance connector: `/hummingbot/connector/exchange/binance/`
- Bybit connector: `/hummingbot/connector/exchange/bybit/`
- Exchange base class: `/hummingbot/connector/exchange_base.py`

### Apex 코드
- **avellaneda_client.py** - 메인 클라이언트 (재사용할 코드)
- **apex/lib/apex_client.py** - Base SDK wrapper
- **apex/common/** - 공통 모듈

---

## ⏱️ 예상 일정 (Estimated Timeline)

| Phase | 작업 | 예상 시간 | 상태 |
|-------|------|----------|------|
| **Phase 1** | Setup & Documentation | 1시간 | ✅ 완료 |
| **Build Fix** | Terminal restart + reinstall | 10분 | ⏳ 대기 |
| **Phase 2** | Connector structure | 30분 | ⏳ 대기 |
| **Phase 3** | Main connector code | 2시간 | ⏳ 대기 |
| **Phase 4** | Configuration | 30분 | ⏳ 대기 |
| **Phase 5** | Testing | 1시간 | ⏳ 대기 |
| **Phase 6** | Live test | 1시간 | ⏳ 대기 |
| **총 예상** | | **6-7시간** | **1.5시간 완료** |

**현재 진행률**: ~20% (Setup 완료)

---

## 🎯 즉시 실행 체크리스트 (Immediate Action Items)

터미널 재시작 후:

```bash
# ✅ 체크리스트
[ ] 1. 새 터미널 열기
[ ] 2. cd "/c/Users/crypto quant/perpdex farm/hummingbot"
[ ] 3. pip install -e .
[ ] 4. python -c "import hummingbot; print('OK')"
[ ] 5. cd ../apex && python test_imports.py
[ ] 6. Claude에게 "Phase 2 시작" 요청
```

---

## 💡 빠른 복원 명령어 (Quick Restore Commands)

터미널 재시작 후 컨텍스트 복원:

```bash
# 1. 현재 문서 확인
cd "/c/Users/crypto quant/perpdex farm"
cat HUMMINGBOT_INTEGRATION_PROGRESS.md

# 2. Hummingbot 재설치
cd hummingbot
pip install -e .

# 3. 상태 확인
python -c "import hummingbot; print('Hummingbot OK')"
cd ../apex
python test_imports.py

# 4. Claude Code 재시작 후 요청:
# "HUMMINGBOT_INTEGRATION_PROGRESS.md 읽고 Phase 2부터 계속해줘"
```

---

## 🔄 컨텍스트 복원 프롬프트 (Context Restore Prompt)

**Claude Code에게 이렇게 요청하세요**:

```
"HUMMINGBOT_INTEGRATION_PROGRESS.md 파일 읽고 현재 상태 파악해줘.
터미널 재시작했고 Hummingbot 설치 완료했어.
Phase 2 (apex_pro connector 구조 생성)부터 시작하자."
```

또는 영어로:

```
"Read HUMMINGBOT_INTEGRATION_PROGRESS.md and understand current state.
Terminal restarted, Hummingbot installed.
Continue from Phase 2 (create apex_pro connector structure)."
```

---

## 📞 문의사항 (Questions)

문제 발생 시:
1. 이 문서 확인 → **Known Issues** 섹션
2. `HUMMINGBOT_INTEGRATION_GUIDE.md` 확인 → 상세 설명
3. 로그 파일 확인: `hummingbot/hummingbot_install.log`

---

**마지막 업데이트**: 2025-11-12 01:30 AM
**다음 단계**: Terminal restart → Hummingbot install → Phase 2

**준비 완료! 터미널 재시작 후 계속하세요! 🚀**