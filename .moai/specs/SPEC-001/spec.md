# SPEC-001: config.yaml 설정 파일 지원

> 생성일: 2025-12-14
> 완료일: 2025-12-14
> 상태: COMPLETED
> 우선순위: Medium

---

## 1. 개요

### 목적
hedge_mode_bp.py의 하드코딩된 트레이딩 파라미터들을 config.yaml 설정 파일에서 읽어오도록 구현하여 코드 수정 없이 전략 튜닝이 가능하도록 함.

### 범위
- `perpdex/hedge/hedge_mode_bp.py` 수정
- `perpdex/hedge/config.yaml` 신규 생성
- `perpdex/hedge/config_loader.py` 유틸리티 신규 생성

---

## 2. 요구사항 (EARS 형식)

### 2.1 Ubiquitous (시스템 전체)

- **[REQ-U01]** 시스템은 config.yaml 파일이 없어도 기본값으로 정상 동작해야 한다.
- **[REQ-U02]** 모든 설정값은 타입 검증을 거쳐야 한다.

### 2.2 Event-Driven (이벤트 기반)

- **[REQ-E01]** HedgeBot 초기화 시, config.yaml 파일이 존재하면 자동으로 로드해야 한다.
- **[REQ-E02]** config.yaml 로드 실패 시, 경고 로그를 출력하고 기본값을 사용해야 한다.

### 2.3 State-Driven (상태 기반)

- **[REQ-S01]** CLI 인자가 존재하면 config.yaml 값보다 우선해야 한다.
- **[REQ-S02]** config.yaml 값이 존재하면 하드코딩된 기본값보다 우선해야 한다.

### 2.4 Unwanted (금지사항)

- **[REQ-W01]** API 키, 시크릿 등 민감정보는 config.yaml에 포함하면 안 된다.
- **[REQ-W02]** config.yaml이 Git에 커밋되어도 보안 위험이 없어야 한다.

### 2.5 Optional (선택사항)

- **[REQ-O01]** 가능하다면 설정값 변경 시 봇 재시작 없이 핫 리로드 지원.

---

## 3. 설정 파라미터 목록

### 3.1 config.yaml에 포함할 값

| 파라미터 | 현재 하드코딩 위치 | 기본값 | 타입 |
|---------|------------------|--------|-----|
| `position_diff_threshold` | hedge_mode_bp.py:1065 | `0.2` | float |
| `buy_price_multiplier` | hedge_mode_bp.py | `0.998` | float |
| `sell_price_multiplier` | hedge_mode_bp.py | `1.002` | float |
| `order_cancel_timeout` | hedge_mode_bp.py:646 | `10` | int (초) |
| `trading_loop_timeout` | hedge_mode_bp.py | `180` | int (초) |
| `max_retries` | hedge_mode_bp.py | `15` | int |
| `fill_check_interval` | hedge_mode_bp.py | `10` | int (초) |

### 3.2 .env에 유지할 값 (민감정보)

- `BACKPACK_PUBLIC_KEY`
- `BACKPACK_SECRET_KEY`
- `API_KEY_PRIVATE_KEY`
- `LIGHTER_ACCOUNT_INDEX`
- `LIGHTER_API_KEY_INDEX`

---

## 4. 설정 우선순위

```
CLI 인자 (최우선)
    ↓
config.yaml
    ↓
하드코딩 기본값 (최하위)
```

---

## 5. config.yaml 구조

```yaml
# Delta Neutral Volume Farming Bot Configuration
# API 키는 .env에서 관리 (이 파일은 Git에 커밋 가능)

trading:
  # 포지션 불균형 허용치 (|Backpack + Lighter| 기준)
  position_diff_threshold: 0.2

  # 주문 취소 타임아웃 (초)
  order_cancel_timeout: 10

  # 트레이딩 루프 타임아웃 (초)
  trading_loop_timeout: 180

  # 최대 재시도 횟수
  max_retries: 15

  # 체결 확인 간격 (초)
  fill_check_interval: 10

pricing:
  # 매수가 조정 (시장가 × 이 값)
  buy_price_multiplier: 0.998

  # 매도가 조정 (진입가 × 이 값)
  sell_price_multiplier: 1.002
```

---

## 6. 구현 계획

### Phase 1: config_loader.py 생성

```python
# perpdex/hedge/config_loader.py
from pathlib import Path
from typing import Any, Optional
import yaml

class ConfigLoader:
    """Load and manage configuration from config.yaml"""

    DEFAULT_CONFIG = {
        'trading': {
            'position_diff_threshold': 0.2,
            'order_cancel_timeout': 10,
            'trading_loop_timeout': 180,
            'max_retries': 15,
            'fill_check_interval': 10,
        },
        'pricing': {
            'buy_price_multiplier': 0.998,
            'sell_price_multiplier': 1.002,
        }
    }

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or 'config.yaml'
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Load config from file, fallback to defaults"""
        ...

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get config value with fallback"""
        ...
```

### Phase 2: hedge_mode_bp.py 수정

1. ConfigLoader import
2. `__init__`에서 config 로드
3. 하드코딩된 값들을 `self.config.get()` 호출로 대체

### Phase 3: 테스트

- config.yaml 없을 때 기본값 동작 확인
- config.yaml 있을 때 값 로드 확인
- CLI 우선순위 확인

---

## 7. 테스트 케이스

### 7.1 Unit Tests

```python
def test_config_loader_defaults():
    """config.yaml 없을 때 기본값 반환"""

def test_config_loader_from_file():
    """config.yaml에서 값 로드"""

def test_config_loader_type_validation():
    """잘못된 타입 시 에러 또는 기본값"""

def test_cli_overrides_config():
    """CLI 인자가 config.yaml보다 우선"""
```

### 7.2 Integration Tests

```python
def test_hedgebot_uses_config():
    """HedgeBot이 config 값 사용"""
```

---

## 8. 파일 변경 목록

| 파일 | 변경 유형 | 설명 |
|-----|---------|------|
| `perpdex/hedge/config_loader.py` | 신규 | 설정 로더 클래스 |
| `perpdex/hedge/config.yaml` | 신규 | 기본 설정 템플릿 |
| `perpdex/hedge/hedge_mode_bp.py` | 수정 | 하드코딩 → config 사용 |
| `perpdex/hedge/tests/test_config_loader.py` | 신규 | 단위 테스트 |

---

## 9. 완료 기준

- [x] config_loader.py 구현 완료 ✅
- [x] config.yaml 템플릿 생성 ✅
- [x] hedge_mode_bp.py 수정 완료 ✅
- [x] 테스트 커버리지 (14/14 tests passed) ✅
- [x] 문서화 완료 ✅

---

## 10. 참고

- 관련 분석: [PARAMETERS_ANALYSIS.md](../../perpdex/hedge/docs/PARAMETERS_ANALYSIS.md)
- 계획 문서: [Plan](../../../.claude/plans/rustling-swinging-thompson.md)
