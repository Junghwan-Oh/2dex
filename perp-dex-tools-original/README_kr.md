##### Follow Me - **X (Twitter)**: [@yourQuantGuy](https://x.com/yourQuantGuy)

---

**Languages**: [🇺🇸 English](README.md) | [🇰🇷 한국어](README_kr.md)

---

## 📢 공유 안내

**공유를 환영합니다!** 이 코드를 공유하거나 수정하는 경우, 원본 저장소에 대한 출처를 명시해주시기 바랍니다. 오픈소스 커뮤니티의 성장을 장려하지만, 원 저작자의 작업에 대한 존중과 인정을 유지해주시기 바랍니다.

---

## 멀티 거래소 트레이딩 봇

EdgeX, Backpack, Paradex, Aster, Lighter, GRVT, Extended를 포함한 다양한 거래소를 지원하는 모듈형 트레이딩 봇입니다. 이 봇은 자동으로 주문을 생성하고 이익을 내며 자동으로 청산하는 전략을 구현합니다.

## 추천 링크 (수수료 리베이트 및 혜택)

#### EdgeX: [https://pro.edgex.exchange/referral/QUANT](https://pro.edgex.exchange/referral/QUANT)

즉시 VIP 1 거래 수수료; 10% 수수료 리베이트; 10% 보너스 포인트

#### Backpack: [https://backpack.exchange/join/quant](https://backpack.exchange/join/quant)

모든 거래 수수료의 35% 리베이트

#### Paradex: [https://app.paradex.trade/r/quant](https://app.paradex.trade/r/quant)

10% 테이커 수수료 할인 리베이트 및 향후 혜택

#### Aster: [https://www.asterdex.com/zh-CN/referral/5191B1](https://www.asterdex.com/zh-CN/referral/5191B1)

30% 수수료 리베이트 및 포인트 부스트

#### grvt: [https://grvt.io/exchange/sign-up?ref=QUANT](https://grvt.io/exchange/sign-up?ref=QUANT)
1.3배 포인트 부스트; 리베이트 (자동 리베이트 시스템은 10월 중순 출시 예정); 프라이빗 트레이딩 대회 참가권

#### Extended: [https://app.extended.exchange/join/QUANT](https://app.extended.exchange/join/QUANT)
10% 수수료 할인; 포인트 부스트 (블랙박스이지만, Extended 공식 문서에서 "다른 계정으로 자신을 추천하는 것보다 제휴 추천 프로그램에서 더 많은 포인트를 받을 것입니다"라고 인용됨); 프라이빗 트레이딩 대회 참가권

#### ApeX: [https://join.omni.apex.exchange/quant]( https://join.omni.apex.exchange/quant)
30% 수수료 리베이트; 5% 수수료 할인; 포인트 부스트


## 설치

1. **저장소 클론**:

   ```bash
   git clone <repository-url>
   cd perp-dex-tools
   ```

2. **가상 환경 생성 및 활성화**:

   먼저, 현재 활성화된 가상 환경이 없는지 확인하세요:

   ```bash
   deactivate
   ```

   가상 환경 생성:

   ```bash
   python3 -m venv env
   ```

   가상 환경 활성화 (스크립트를 사용할 때마다 가상 환경을 활성화해야 합니다):

   ```bash
   source env/bin/activate  # Windows: env\Scripts\activate
   ```

3. **종속성 설치**:
   먼저, 현재 활성화된 가상 환경이 없는지 확인하세요:

   ```bash
   deactivate
   ```

   가상 환경 활성화 (스크립트를 사용할 때마다 가상 환경을 활성화해야 합니다):

   ```bash
   source env/bin/activate  # Windows: env\Scripts\activate
   ```

   ```bash
   pip install -r requirements.txt
   ```

   **Paradex 사용자**: Paradex 거래소를 사용하려면 추가 가상 환경을 생성하고 Paradex 전용 종속성을 설치해야 합니다:

   먼저, 현재 활성화된 가상 환경이 없는지 확인하세요:

   ```bash
   deactivate
   ```

   Paradex 전용 가상 환경 생성 (para_env라는 이름으로):

   ```bash
   python3 -m venv para_env
   ```

   가상 환경 활성화 (스크립트를 사용할 때마다 가상 환경을 활성화해야 합니다):

   ```bash
   source para_env/bin/activate  # Windows: para_env\Scripts\activate
   ```

   Paradex 종속성 설치

   ```bash
   pip install -r para_requirements.txt
   ```

   **Apex 사용자**: Apex 거래소를 사용하려면 Apex 종속성을 설치해야 합니다:

   먼저, 현재 활성화된 가상 환경이 없는지 확인하세요:

   ```bash
   source env/bin/activate  # Windows: env\Scripts\activate
   ```

   Apex 종속성 설치

   ```bash
   pip install -r apex_requirements.txt
   ```

4. **환경 변수 설정**:
   프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 env_example.txt를 템플릿으로 사용하여 API 키를 수정하세요.

5. **텔레그램 봇 설정 (선택사항)**:
   거래 알림을 받으려면 [텔레그램 봇 설정 가이드](docs/telegram-bot-setup.md)를 참조하여 텔레그램 봇을 설정하세요.

## 전략 개요

**중요 안내**: 모든 사용자는 먼저 이 스크립트의 로직과 위험을 이해하여 자신에게 더 적합한 매개변수를 설정할 수 있도록 해야 하며, 또는 이것이 좋은 전략이 아니라고 생각하여 전혀 사용하지 않을 수도 있습니다. 트위터에서 언급했듯이, 저는 이러한 스크립트를 공유 목적으로 작성한 것이 아니라 실제로 이 스크립트를 사용하고 있기 때문에 작성했고, 그 다음에 공유했습니다.
이 스크립트는 주로 장기적인 마모에 초점을 맞춥니다. 스크립트가 계속해서 주문을 생성하는 한, 한 달 후에 가격이 최고 물린 지점에 도달하면 그 달의 모든 거래량은 제로 마모가 됩니다. 따라서 저는 `--quantity`와 `--wait-time`을 너무 작게 설정하는 것이 좋은 장기 전략이 아니라고 생각하지만, 단기 고강도 볼륨 거래에는 실제로 적합합니다. 저는 일반적으로 시장이 판단에 반대되더라도 스크립트가 진입 지점으로 가격이 돌아올 때까지 지속적이고 안정적으로 주문을 생성할 수 있도록 quantity를 40-60, wait-time을 450-650 사이로 사용하여 제로 마모 볼륨 거래를 달성합니다.

봇은 간단한 거래 전략을 구현합니다:

1. **주문 생성**: 현재 시장 가격 근처에 지정가 주문 생성
2. **주문 모니터링**: 주문 체결 대기
3. **청산 주문**: 익절 수준에서 자동으로 청산 주문 생성
4. **포지션 관리**: 포지션 및 활성 주문 모니터링
5. **위험 관리**: 최대 동시 주문 수 제한
6. **그리드 스텝 제어**: `--grid-step` 매개변수를 통해 새 주문과 기존 청산 주문 간 최소 가격 거리 제어
7. **거래 중지 제어**: `--stop-price` 매개변수를 통해 거래 중지 가격 조건 제어

#### ⚙️ 주요 매개변수

- **quantity**: 주문당 거래 수량
- **take-profit**: 익절 비율 (예: 0.02는 0.02%를 의미)
- **max-orders**: 최대 동시 활성 주문 수 (위험 제어)
- **wait-time**: 주문 간 대기 시간 (과도한 거래 방지)
- **grid-step**: 그리드 스텝 제어 (청산 주문이 너무 밀집되지 않도록 방지)
- **stop-price**: `direction`이 'buy'일 때, 가격 >= stop-price이면 종료; 'sell' 로직은 반대 (기본값: -1, 가격 기반 종료 없음)
- **pause-price**: `direction`이 'buy'일 때, 가격 >= pause-price이면 일시 중지; 'sell' 로직은 반대 (기본값: -1, 가격 기반 일시 중지 없음)

#### 그리드 스텝 기능

`--grid-step` 매개변수는 새 주문 청산 가격과 기존 청산 주문 가격 간의 최소 거리를 제어합니다:

- **기본값 -100**: 그리드 스텝 제한 없음, 원래 전략 실행
- **양수 값 (예: 0.5)**: 새 주문 청산 가격은 가장 가까운 청산 주문 가격으로부터 최소 0.5% 거리를 유지해야 함
- **목적**: 청산 주문이 너무 밀집되지 않도록 방지하여 체결 확률 및 위험 관리 개선

예를 들어, 롱 포지션이고 `--grid-step 0.5`일 때:

- 기존 청산 주문 가격이 2000 USDT라면
- 새 주문 청산 가격은 1990 USDT (2000 × (1 - 0.5%)) 미만이어야 함
- 이것은 청산 주문이 너무 가까이 있는 것을 방지하여 전체 전략 효과를 개선함

#### 📊 거래 흐름 예시

현재 ETH 가격이 $2000이고 익절이 0.02%로 설정되어 있다고 가정:

1. **포지션 오픈**: $2000.40에 매수 주문 생성 (시장 가격보다 약간 높음)
2. **체결**: 주문이 시장에서 체결되어 롱 포지션 획득
3. **포지션 청산**: 즉시 $2000.80에 매도 주문 생성 (익절 가격)
4. **완료**: 청산 주문이 체결되어 0.02% 이익 획득
5. **반복**: 다음 거래 사이클로 계속

#### 🛡️ 위험 관리

- **주문 제한**: `max-orders`를 통해 최대 동시 주문 수 제한
- **그리드 제어**: `grid-step`을 통해 청산 주문 간 합리적인 간격 보장
- **주문 빈도 제어**: `wait-time`을 통해 주문 타이밍 제어하여 단기간에 물리지 않도록 방지
- **실시간 모니터링**: 포지션 및 주문 상태를 지속적으로 모니터링
- **⚠️ 손절 없음**: 이 전략은 손절 기능을 포함하지 않으며 불리한 시장 상황에서 상당한 손실을 입을 수 있음

## 샘플 명령어:

### EdgeX 거래소:

ETH:

```bash
python runbot.py --exchange edgex --ticker ETH --quantity 0.1 --take-profit 0.02 --max-orders 40 --wait-time 450
```

ETH (그리드 스텝 제어 포함):

```bash
python runbot.py --exchange edgex --ticker ETH --quantity 0.1 --take-profit 0.02 --max-orders 40 --wait-time 450 --grid-step 0.5
```

ETH (중지 가격 제어 포함):

```bash
python runbot.py --exchange edgex --ticker ETH --quantity 0.1 --take-profit 0.02 --max-orders 40 --wait-time 450 --stop-price 5500
```

BTC:

```bash
python runbot.py --exchange edgex --ticker BTC --quantity 0.05 --take-profit 0.02 --max-orders 40 --wait-time 450
```

### Backpack 거래소:

ETH 무기한:

```bash
python runbot.py --exchange backpack --ticker ETH --quantity 0.1 --take-profit 0.02 --max-orders 40 --wait-time 450
```

ETH 무기한 (그리드 스텝 제어 포함):

```bash
python runbot.py --exchange backpack --ticker ETH --quantity 0.1 --take-profit 0.02 --max-orders 40 --wait-time 450 --grid-step 0.3
```

ETH 무기한 (부스트 모드 활성화):

```bash
python runbot.py --exchange backpack --ticker ETH --direction buy --quantity 0.1 --boost
```

### Aster 거래소:

ETH:

```bash
python runbot.py --exchange aster --ticker ETH --quantity 0.1 --take-profit 0.02 --max-orders 40 --wait-time 450
```

ETH (부스트 모드 활성화):

```bash
python runbot.py --exchange aster --ticker ETH --direction buy --quantity 0.1 --boost
```

### GRVT 거래소:

BTC:

```bash
python runbot.py --exchange grvt --ticker BTC --quantity 0.05 --take-profit 0.02 --max-orders 40 --wait-time 450
```

### Extended 거래소:

ETH:

```bash
python runbot.py --exchange extended --ticker ETH --quantity 0.1 --take-profit 0 --max-orders 40 --wait-time 450 --grid-step 0.01
```

## 🆕 헤지 모드

새로운 헤지 모드 (`hedge_mode.py`)는 두 거래소에서 동시에 헤지 거래를 수행하여 위험을 줄이는 거래 전략입니다:

### 헤지 모드 작동 방식

1. **오픈 단계**: 선택한 거래소(예: Backpack)에 메이커 주문 생성
2. **헤지 단계**: 주문 체결 후 즉시 Lighter에 시장가 주문을 생성하여 헤지
3. **청산 단계**: 선택한 거래소에 포지션 청산을 위한 또 다른 메이커 주문 생성
4. **헤지 청산**: Lighter에 시장가 주문을 생성하여 헤지 포지션 청산

### 헤지 모드 사용 예시

```bash
# Backpack으로 BTC 헤지 모드 실행
python hedge_mode.py --exchange backpack --ticker BTC --size 0.05 --iter 20 --max-position 1

# Extended로 ETH 헤지 모드 실행
python hedge_mode.py --exchange extended --ticker ETH --size 0.1 --iter 20

# Apex로 BTC 헤지 모드 실행
python hedge_mode.py --exchange apex --ticker BTC --size 0.05 --iter 20

# GRVT로 BTC 헤지 모드 실행
python hedge_mode.py --exchange grvt --ticker BTC --size 0.05 --iter 20

# edgeX로 BTC 헤지 모드 실행
python hedge_mode.py --exchange edgex --ticker BTC --size 0.001 --iter 20
```

### 헤지 모드 매개변수

- `--exchange`: 주요 거래소 ('backpack', 'extended', 'apex', 'grvt', 'edgex' 지원)
- `--ticker`: 거래 쌍 심볼 (예: BTC, ETH)
- `--size`: 거래당 주문 수량
- `--iter`: 거래 사이클 수
- `--fill-timeout`: 메이커 주문 체결 타임아웃 (초 단위, 기본값: 5)
- `--sleep`: 각 단계 후 대기 시간 (초 단위, 기본값: 0)
- `--max-position`: 이 매개변수가 설정되면 헤지 모드는 헤지를 수행하면서 지정된 최대 크기까지 포지션을 점진적으로 구축합니다. 단위는 기본 자산입니다. 예를 들어 BTC를 실행할 때 0.1로 설정하면 헤지하면서 최대 0.1 BTC까지 포지션을 점진적으로 구축합니다.

## 설정

### 환경 변수

#### 일반 설정

- `ACCOUNT_NAME`: 환경 변수의 현재 계정 이름, 여러 계정 로그를 구분하는 데 사용, 사용자 정의 가능, 필수 아님

#### 텔레그램 설정 (선택사항)

- `TELEGRAM_BOT_TOKEN`: 텔레그램 봇 토큰
- `TELEGRAM_CHAT_ID`: 텔레그램 채팅 ID

#### EdgeX 설정

- `EDGEX_ACCOUNT_ID`: EdgeX 계정 ID
- `EDGEX_STARK_PRIVATE_KEY`: EdgeX API 개인키
- `EDGEX_BASE_URL`: EdgeX API 기본 URL (기본값: https://pro.edgex.exchange)
- `EDGEX_WS_URL`: EdgeX WebSocket URL (기본값: wss://quote.edgex.exchange)

#### Backpack 설정

- `BACKPACK_PUBLIC_KEY`: Backpack API 키
- `BACKPACK_SECRET_KEY`: Backpack API Secret

#### Paradex 설정

- `PARADEX_L1_ADDRESS`: L1 지갑 주소
- `PARADEX_L2_PRIVATE_KEY`: L2 지갑 개인키 (아바타, 지갑, "paradex private key 복사" 클릭)

#### Aster 설정

- `ASTER_API_KEY`: Aster API 키
- `ASTER_SECRET_KEY`: Aster API Secret

#### Lighter 설정

- `API_KEY_PRIVATE_KEY`: Lighter API 개인키
- `LIGHTER_ACCOUNT_INDEX`: Lighter 계정 인덱스
- `LIGHTER_API_KEY_INDEX`: Lighter API 키 인덱스

#### GRVT 설정

- `GRVT_TRADING_ACCOUNT_ID`: GRVT 거래 계정 ID
- `GRVT_PRIVATE_KEY`: GRVT 개인키
- `GRVT_API_KEY`: GRVT API 키

#### Extended 설정

- `EXTENDED_API_KEY`: Extended API 키
- `EXTENDED_STARK_KEY_PUBLIC`: Stark 공개키
- `EXTENDED_STARK_KEY_PRIVATE`: Stark 개인키
- `EXTENDED_VAULT`: Extended Vault ID

#### Apex 설정

- `APEX_API_KEY`: Apex API 키
- `APEX_API_KEY_PASSPHRASE`: Apex API 키 패스프레이즈
- `APEX_API_KEY_SECRET`: Apex API 키 시크릿
- `APEX_OMNI_KEY_SEED`: Apex Omni 키 시드

**LIGHTER_ACCOUNT_INDEX 얻는 방법**:

1. 다음 URL 끝에 지갑 주소를 추가하세요:

   ```
   https://mainnet.zklighter.elliot.ai/api/v1/account?by=l1_address&value=
   ```

2. 브라우저에서 이 URL을 여세요

3. 결과에서 "account_index"를 검색하세요 - 서브 계정이 있는 경우 여러 account_index 값이 있습니다. 짧은 것이 메인 계정이고 긴 것들이 서브 계정입니다.

### 명령줄 인수

- `--exchange`: 사용할 거래소: 'edgex', 'backpack', 'paradex', 'aster', 'lighter', 'grvt', 또는 'extended' (기본값: edgex)
- `--ticker`: 기본 자산 심볼 (예: ETH, BTC, SOL). 계약 ID는 자동으로 해결됩니다.
- `--quantity`: 주문 수량 (기본값: 0.1)
- `--take-profit`: 익절 비율 (예: 0.02는 0.02%를 의미)
- `--direction`: 거래 방향: 'buy' 또는 'sell' (기본값: buy)
- `--env-file`: 계정 설정 파일 (기본값: .env)
- `--max-orders`: 최대 활성 주문 수 (기본값: 40)
- `--wait-time`: 주문 간 대기 시간 (초 단위, 기본값: 450)
- `--grid-step`: 다음 청산 주문 가격까지의 최소 거리 비율 (기본값: -100, 제한 없음을 의미)
- `--stop-price`: `direction`이 'buy'일 때, 가격 >= stop-price이면 거래를 중지하고 프로그램을 종료; 'sell' 로직은 반대 (기본값: -1, 가격 기반 종료 없음). 이 매개변수의 목적은 "롱 포지션의 고점 또는 숏 포지션의 저점이라고 생각하는 곳"에서 주문이 생성되는 것을 방지하는 것입니다.
- `--pause-price`: `direction`이 'buy'일 때, 가격 >= pause-price이면 거래를 일시 중지하고 가격이 pause-price 아래로 떨어지면 거래를 재개; 'sell' 로직은 반대 (기본값: -1, 가격 기반 일시 중지 없음). 이 매개변수의 목적은 "롱 포지션의 고점 또는 숏 포지션의 저점이라고 생각하는 곳"에서 주문이 생성되는 것을 방지하는 것입니다.
- `--boost`: Aster 및 Backpack 거래소에서 볼륨 부스팅을 위한 부스트 모드 활성화 ('aster' 및 'backpack'에서만 사용 가능)
  부스트 거래 로직: 메이커 주문으로 포지션을 열고, 체결 후 즉시 테이커 주문으로 청산, 이 사이클을 반복합니다. 마모는 메이커 주문 하나, 테이커 주문 하나의 수수료와 슬리피지로 구성됩니다.

## 로깅

봇은 포괄적인 로깅을 제공합니다:

- **거래 로그**: 주문 세부 정보가 포함된 CSV 파일
- **디버그 로그**: 타임스탬프가 있는 상세 활동 로그
- **콘솔 출력**: 실시간 상태 업데이트
- **오류 처리**: 포괄적인 오류 로깅 및 처리

## Q & A

### 같은 장치에서 같은 거래소에 대해 여러 계정을 구성하는 방법은?

1. 각 계정에 대해 .env 파일을 생성하세요, 예: account_1.env, account_2.env
2. 각 계정의 .env 파일에 `ACCOUNT_NAME=`을 설정하세요, 예: `ACCOUNT_NAME=MAIN`.
3. 각 파일에 각 계정의 API 키 또는 시크릿을 구성하세요
4. 명령줄에서 다른 `--env-file` 매개변수를 사용하여 다른 계정을 시작하세요, 예: `python runbot.py --env-file account_1.env [다른 매개변수...]`

### 같은 장치에서 다른 거래소에 대해 여러 계정을 구성하는 방법은?

같은 `.env` 파일에 모든 다른 거래소 계정을 구성한 다음, 명령줄에서 다른 `--exchange` 매개변수를 사용하여 다른 거래소를 시작하세요, 예: `python runbot.py --exchange backpack [다른 매개변수...]`

### 같은 장치에서 같은 계정과 거래소에 대해 여러 계약을 구성하는 방법은?

`.env` 파일에 계정을 구성한 다음, 명령줄에서 다른 `--ticker` 매개변수를 사용하여 다른 계약을 시작하세요, 예: `python runbot.py --ticker ETH [다른 매개변수...]`

## 기여

1. 저장소 포크
2. 기능 브랜치 생성
3. 변경사항 작성
4. 해당하는 경우 테스트 추가
5. Pull Request 제출

## 라이센스

이 프로젝트는 비상업적 라이센스에 따라 라이센스가 부여됩니다 - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

**중요 안내**: 이 소프트웨어는 개인 학습 및 연구 목적으로만 사용됩니다. 상업적 사용은 엄격히 금지됩니다. 상업적 사용을 위해서는 작성자에게 상업 라이센스를 문의하세요.

## 면책 조항

이 소프트웨어는 교육 및 연구 목적으로만 사용됩니다. 암호화폐 거래는 상당한 위험을 수반하며 상당한 재정적 손실을 초래할 수 있습니다. 자신의 책임하에 사용하고 잃을 여유가 없는 돈으로는 절대 거래하지 마세요.
