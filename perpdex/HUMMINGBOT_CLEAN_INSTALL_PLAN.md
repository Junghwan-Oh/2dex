# 허밍봇 Avellaneda MM 실행 계획

**목표**: 허밍봇에서 Avellaneda MM 전략 구동
**예상 시간**: 3시간
**날짜**: 2025-11-13

---

## Step 1: 백업 (5분)

```bash
cd "C:/Users/crypto quant/perpdex"
mkdir hummingbot_backup

# 필수 파일만 백업
cp hummingbot/conf/strategies/apex_pro_avellaneda_eth_usdt.yml hummingbot_backup/
cp -r hummingbot/hummingbot/connector/exchange/apex_pro/ hummingbot_backup/
cp apex/.env hummingbot_backup/
```

**체크**: 백업 폴더에 3개 항목 확인

---

## Step 2: 기존 삭제 (5분)

```bash
cd "C:/Users/crypto quant/perpdex"
rm -rf hummingbot
```

**체크**: hummingbot 폴더 삭제됨

---

## Step 3: Clean Install (2시간)

### 3.1 Python 3.12 환경

```bash
conda deactivate
conda env remove -n hummingbot
conda create -n hummingbot python=3.12 -y
conda activate hummingbot

# 검증
python --version  # 3.12.x 확인
```

### 3.2 UTF-8 설정

```powershell
# PowerShell에서
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
```

### 3.3 공식 설치

```bash
cd "C:/Users/crypto quant/perpdex"
git clone https://github.com/hummingbot/hummingbot.git
cd hummingbot

# Git Bash에서 실행
./install

# 컴파일
python setup.py build_ext --inplace

# 검증
hummingbot
>>> status
>>> exit
```

**체크**: hummingbot CLI 정상 실행

---

## Step 4: 커넥터 복원 (10분)

```bash
cd "C:/Users/crypto quant/perpdex/hummingbot"

# 커넥터 복사
cp -r ../hummingbot_backup/apex_pro/ hummingbot/connector/exchange/

# 전략 설정 복사
cp ../hummingbot_backup/apex_pro_avellaneda_eth_usdt.yml conf/strategies/
```

**체크**: 파일 존재 확인

---

## Step 5: API 연결 (10분)

```bash
hummingbot
>>> connect apex_pro
```

입력 항목:
- API Key
- API Secret
- API Passphrase
- ZK Seeds
- ZK L2 Key

```bash
>>> status
```

**체크**: 잔고 표시되면 성공

---

## Step 6: 전략 실행

```bash
>>> import
# 파일 선택: apex_pro_avellaneda_eth_usdt.yml

>>> start
```

**체크**: 주문 생성 로그 확인

---

## 문제 해결

### ./install 실패
- Git Bash 설치 확인
- 관리자 권한 실행

### APEX-TIMESTAMP 에러
```bash
w32tm /resync
```

### cp949 인코딩 에러
- PYTHONUTF8=1 재확인

---

## 성공 기준

- [ ] hummingbot CLI 실행
- [ ] APEX Pro 연결 성공
- [ ] 잔고 조회 성공
- [ ] Avellaneda 전략 로드
- [ ] 주문 생성 확인

---

**핵심**: `./install` 스크립트만 믿는다.
