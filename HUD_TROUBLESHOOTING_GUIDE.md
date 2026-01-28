# Claude Code HUD (oh-my-claudecode) 완전 가이드

**작성일**: 2026-01-25
**목적**: VSCode/Claude Code 재시작 후 HUD 맥락 복원 및 테스트

---

## 📋 목차
1. [문제 배경](#문제-배경)
2. [해결된 설정](#해결된-설정)
3. [HUD 아키텍처](#hud-아키텍처)
4. [파일 위치 및 내용](#파일-위치-및-내용)
5. [테스트 방법](#테스트-방법)
6. [진단 절차](#진단-절차)
7. [알려진 동작](#알려진-동작)

---

## 문제 배경

### 증상
- Claude Code HUD (oh-my-claudecode 플러그인의 statusLine 기능)가 표시되지 않음
- 상태바에 OMC 정보가 나타나지 않음

### 원인
`~/.claude/settings.json`의 `statusLine.command` 경로가 존재하지 않는 위치를 가리키고 있었음:
```json
"statusLine": {
  "command": "C:/claude-hud/hud/index.js"  // ❌ 존재하지 않는 경로
}
```

### 해결책
실제 HUD 스크립트 위치로 경로 수정 (사용자명에 공백이 있어 따옴표 필요):
```json
"statusLine": {
  "type": "command",
  "command": "node \"C:/Users/crypto quant/.claude/hud/omc-hud.mjs\""
}
```

---

## 해결된 설정

### 현재 설정 파일: `C:/Users/crypto quant/.claude/settings.json`

```json
{
  "permissions": {
    "allow": [
      "Bash(git clone:*)"
    ]
  },
  "enabledPlugins": {
    "oh-my-claudecode@omc": true
  },
  "statusLine": {
    "type": "command",
    "command": "node \"C:/Users/crypto quant/.claude/hud/omc-hud.mjs\""
  },
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "cbb53199adec4f3b9c8fe82232f0acf4.x8v0kN9zndvUW26S",
    "ANTHROPIC_BASE_URL": "https://api.z.ai/api/anthropic",
    "API_TIMEOUT_MS": "300000",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "glm-4.7",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "glm-4.7",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "glm-4.7-flash"
  },
  "pluginConfigs": {
    "context7@anthropic-tools": {
      "mcpServers": {}
    },
    "filesystem@anthropic-tools": {
      "mcpServers": {
        "filesystem": {
          "allowedDirectories": [
            "f:\\Dropbox\\dexbot"
          ]
        }
      }
    }
  }
}
```

---

## HUD 아키텍처

### 구조도
```
Claude Code (실행 중)
    ↓ (statusLine.command 호출)
    ↓ (stdin으로 JSON 전달: cwd, transcript_path, context_window, model 등)
    ↓
omc-hud.mjs (wrapper script)
    ↓ (플러그인 캐시에서 실제 HUD 로드)
    ↓
~/.claude/plugins/cache/omc/oh-my-claudecode/3.3.10/dist/hud/index.js
    ↓ (stdin 파싱, transcript 분석, 상태 읽기)
    ↓ (render.js로 포맷팅)
    ↓ (stdout으로 출력)
    ↓
Claude Code 상태바에 표시
```

### 데이터 흐름

**Claude Code → HUD (stdin JSON)**:
```json
{
  "cwd": "/current/working/directory",
  "transcript_path": "/path/to/conversation.jsonl",
  "context_window": {
    "context_window_size": 200000,
    "current_usage": {
      "input_tokens": 12345,
      "cache_creation_input_tokens": 5000,
      "cache_read_input_tokens": 3000
    },
    "used_percentage": 15.5
  },
  "model": {
    "id": "claude-sonnet-4-5-20250929",
    "display_name": "Sonnet 4.5"
  }
}
```

**HUD → Claude Code (stdout text)**:
```
[포맷된 상태바 텍스트: 컨텍스트%, 모델명, TODO, 에이전트 상태 등]
```

---

## 파일 위치 및 내용

### 1. Wrapper Script: `C:/Users/crypto quant/.claude/hud/omc-hud.mjs`

**역할**: 플러그인 캐시 또는 개발 경로에서 실제 HUD 구현을 찾아 로드

```javascript
#!/usr/bin/env node
/**
 * OMC HUD - Statusline Script
 * Wrapper that imports from plugin cache or development paths
 */

import { existsSync, readdirSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

async function main() {
  const home = homedir();

  // 1. Try plugin cache first (marketplace: omc, plugin: oh-my-claudecode)
  const pluginCacheBase = join(home, ".claude/plugins/cache/omc/oh-my-claudecode");
  if (existsSync(pluginCacheBase)) {
    try {
      const versions = readdirSync(pluginCacheBase);
      if (versions.length > 0) {
        const latestVersion = versions.sort().reverse()[0];
        const pluginPath = join(pluginCacheBase, latestVersion, "dist/hud/index.js");
        if (existsSync(pluginPath)) {
          await import(pathToFileURL(pluginPath).href);
          return;
        }
      }
    } catch { /* continue */ }
  }

  // 2. Development paths
  const devPaths = [
    join(home, "Workspace/oh-my-claude-sisyphus/dist/hud/index.js"),
    join(home, "workspace/oh-my-claude-sisyphus/dist/hud/index.js"),
    join(home, "Workspace/oh-my-claudecode/dist/hud/index.js"),
    join(home, "workspace/oh-my-claudecode/dist/hud/index.js"),
  ];

  for (const devPath of devPaths) {
    if (existsSync(devPath)) {
      try {
        await import(pathToFileURL(devPath).href);
        return;
      } catch { /* continue */ }
    }
  }

  // 3. Fallback
  console.log("[OMC] run /omc-setup to install properly");
}

main();
```

### 2. HUD 구현: `C:/Users/crypto quant/.claude/plugins/cache/omc/oh-my-claudecode/3.3.10/dist/hud/`

**디렉토리 구조**:
```
dist/hud/
├── index.js              # 메인 진입점
├── stdin.js              # stdin JSON 파싱
├── render.js             # 출력 포맷팅
├── state.js              # HUD 상태 읽기
├── transcript.js         # 대화 transcript 파싱
├── omc-state.js          # OMC 모드 상태 (ralph, ultrawork 등)
├── usage-api.js          # API 사용량 조회
├── background-tasks.js   # 백그라운드 작업 추적
└── colors.js             # 색상 코드
```

### 3. stdin.js - 핵심 입력 처리

```javascript
/**
 * OMC HUD - Stdin Parser
 *
 * Parse stdin JSON from Claude Code statusline interface.
 */

/**
 * Read and parse stdin JSON from Claude Code.
 * Returns null if stdin is not available or invalid.
 */
export async function readStdin() {
    // Skip if running in TTY mode (interactive terminal)
    if (process.stdin.isTTY) {
        return null;
    }
    const chunks = [];
    try {
        process.stdin.setEncoding('utf8');
        for await (const chunk of process.stdin) {
            chunks.push(chunk);
        }
        const raw = chunks.join('');
        if (!raw.trim()) {
            return null;
        }
        return JSON.parse(raw);
    }
    catch {
        return null;
    }
}

/**
 * Get context window usage percentage.
 * Prefers native percentage from Claude Code v2.1.6+, falls back to manual calculation.
 */
export function getContextPercent(stdin) {
    // Prefer native percentage (v2.1.6+) - accurate and matches /context
    const nativePercent = stdin.context_window?.used_percentage;
    if (typeof nativePercent === 'number' && !Number.isNaN(nativePercent)) {
        return Math.min(100, Math.max(0, Math.round(nativePercent)));
    }
    // Fallback: manual calculation
    const size = stdin.context_window?.context_window_size;
    if (!size || size <= 0) {
        return 0;
    }
    const totalTokens = getTotalTokens(stdin);
    return Math.min(100, Math.round((totalTokens / size) * 100));
}

/**
 * Get model display name from stdin.
 */
export function getModelName(stdin) {
    return stdin.model?.display_name ?? stdin.model?.id ?? 'Unknown';
}
```

### 4. index.js - 메인 로직 (요약)

```javascript
#!/usr/bin/env node
/**
 * OMC HUD - Main Entry Point
 *
 * Statusline command that visualizes oh-my-claudecode state.
 * Receives stdin JSON from Claude Code and outputs formatted statusline.
 */
import { readStdin, getContextPercent, getModelName } from './stdin.js';
import { parseTranscript } from './transcript.js';
import { readHudState, readHudConfig, getRunningTasks } from './state.js';
import { readRalphStateForHud, readUltraworkStateForHud, readPrdStateForHud, readAutopilotStateForHud } from './omc-state.js';
import { getUsage } from './usage-api.js';
import { render } from './render.js';

async function main() {
    try {
        // Read stdin from Claude Code
        const stdin = await readStdin();
        if (!stdin) {
            // No stdin - suggest setup
            console.log('[OMC] run /omc-setup to install properly');
            return;
        }

        const cwd = stdin.cwd || process.cwd();

        // Parse transcript for agents and todos
        const transcriptData = await parseTranscript(stdin.transcript_path);

        // Read OMC state files
        const ralph = readRalphStateForHud(cwd);
        const ultrawork = readUltraworkStateForHud(cwd);
        const prd = readPrdStateForHud(cwd);
        const autopilot = readAutopilotStateForHud(cwd);

        // Read HUD state for background tasks
        const hudState = readHudState(cwd);

        // Read configuration
        const config = readHudConfig();

        // Fetch rate limits from OAuth API (if available)
        const rateLimits = config.elements.rateLimits !== false
            ? await getUsage()
            : null;

        // Build render context
        const context = {
            contextPercent: getContextPercent(stdin),
            modelName: getModelName(stdin),
            ralph,
            ultrawork,
            prd,
            autopilot,
            activeAgents: transcriptData.agents.filter((a) => a.status === 'running'),
            todos: transcriptData.todos,
            backgroundTasks: getRunningTasks(hudState),
            cwd,
            lastSkill: transcriptData.lastActivatedSkill || null,
            rateLimits,
            pendingPermission: transcriptData.pendingPermission || null,
            thinkingState: transcriptData.thinkingState || null,
            sessionHealth: calculateSessionHealth(transcriptData.sessionStart, getContextPercent(stdin))
        };

        // Render and output
        const output = render(context, config);

        // Replace spaces with non-breaking spaces for terminal alignment
        const formattedOutput = output.replace(/ /g, '\u00A0');
        console.log(formattedOutput);
    }
    catch (error) {
        // On any error, suggest setup
        console.log('[OMC] run /omc-setup to install properly');
    }
}

// Run main
main();
```

---

## 테스트 방법

### ✅ 빠른 검증 체크리스트

1. **설정 파일 확인**:
```bash
cat "C:/Users/crypto quant/.claude/settings.json" | grep -A 3 statusLine
```

예상 출력:
```json
"statusLine": {
  "type": "command",
  "command": "node \"C:/Users/crypto quant/.claude/hud/omc-hud.mjs\""
}
```

2. **Wrapper 스크립트 존재 확인**:
```bash
ls -la "C:/Users/crypto quant/.claude/hud/omc-hud.mjs"
```

예상: 파일이 존재해야 함

3. **플러그인 캐시 확인**:
```bash
ls -la "C:/Users/crypto quant/.claude/plugins/cache/omc/oh-my-claudecode/"
```

예상: `3.3.10/` 디렉토리가 존재해야 함

4. **HUD 구현 파일 확인**:
```bash
ls -la "C:/Users/crypto quant/.claude/plugins/cache/omc/oh-my-claudecode/3.3.10/dist/hud/"
```

예상: `index.js`, `stdin.js`, `render.js` 등이 존재해야 함

### 🧪 수동 테스트

**주의**: 수동으로 HUD 스크립트를 실행하면 **항상** `[OMC] run /omc-setup to install properly` 메시지가 나옵니다. 이것은 **정상 동작**입니다!

#### 왜 이런 메시지가 나오나?

```javascript
// stdin.js의 readStdin() 함수
if (process.stdin.isTTY) {  // 터미널에서 직접 실행하면 true
    return null;  // null 반환
}
```

```javascript
// index.js의 main() 함수
const stdin = await readStdin();
if (!stdin) {  // null이므로 이 조건 충족
    console.log('[OMC] run /omc-setup to install properly');
    return;
}
```

**결론**: 터미널에서 직접 실행하면 TTY 모드로 인식되어 stdin을 읽지 않고 fallback 메시지를 출력합니다. 이것은 정상이며, Claude Code가 호출할 때만 실제 HUD가 렌더링됩니다.

#### stdin 시뮬레이션 테스트

실제 stdin을 제공하여 테스트:

```bash
echo '{"cwd":"/test","transcript_path":"/dev/null","context_window":{"context_window_size":200000,"current_usage":{"input_tokens":5000},"used_percentage":2.5},"model":{"display_name":"Sonnet 4.5"}}' | node "C:/Users/crypto quant/.claude/hud/omc-hud.mjs"
```

예상 출력: 포맷된 상태바 텍스트 (모델명, 컨텍스트% 등)

---

## 진단 절차

### 단계별 진단

#### 1단계: Claude Code 로그 확인

**위치** (추정):
- Windows: `%APPDATA%\.claude\logs\`
- 또는 Claude Code 출력 패널

**확인 사항**:
- statusLine 명령 실행 에러
- Node.js 실행 실패
- 권한 문제

#### 2단계: Node.js 버전 확인

```bash
node --version
```

**요구사항**: Node.js 18+ (ESM 지원 필요)

#### 3단계: 스크립트 실행 권한

```bash
# PowerShell에서:
Get-ExecutionPolicy

# 제한적이면:
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

#### 4단계: 경로 공백 문제 확인

설정에서 경로가 제대로 quoted되어 있는지:
```json
// ✅ 올바름
"command": "node \"C:/Users/crypto quant/.claude/hud/omc-hud.mjs\""

// ❌ 틀림
"command": "node C:/Users/crypto quant/.claude/hud/omc-hud.mjs"
```

#### 5단계: Claude Code 버전 확인

statusLine 기능은 Claude Code 특정 버전 이상 필요:
```bash
# Claude Code CLI에서
claude --version
```

또는 VSCode 확장 버전 확인

#### 6단계: 수동 디버깅 모드

HUD 스크립트에 임시 디버그 로그 추가:

```javascript
// omc-hud.mjs의 main() 함수 시작 부분에:
console.error('[DEBUG] omc-hud.mjs started');
console.error('[DEBUG] Home:', home);
console.error('[DEBUG] Plugin cache:', pluginCacheBase);
```

stderr는 Claude Code 로그에 기록되어야 함

---

## 알려진 동작

### ✅ 정상 동작

1. **Claude Code 실행 중 상태바에 HUD 표시됨**
   - 컨텍스트 사용률 (%)
   - 현재 모델명
   - 활성 TODO 개수
   - 실행 중인 에이전트
   - ralph/ultrawork/autopilot 상태

2. **Claude Code가 대화할 때마다 HUD 업데이트**
   - 실시간 컨텍스트 변화 반영
   - TODO 상태 변화 반영

3. **터미널에서 직접 실행 시 fallback 메시지**
   ```
   [OMC] run /omc-setup to install properly
   ```
   이것은 **에러가 아님** - stdin이 없을 때의 정상 동작

### ❌ 비정상 동작

1. **Claude Code 실행 중인데 HUD가 안 보임**
   - 설정 파일 문제
   - 플러그인 미설치
   - statusLine 명령 실행 실패

2. **HUD가 깜빡이거나 에러 메시지 반복**
   - 스크립트 크래시
   - stdin 파싱 실패
   - 권한 문제

---

## 해결 완료 상태

### ✅ 현재 상태 (2026-01-25)

- [x] settings.json의 statusLine 경로 수정 완료
- [x] 경로에 공백 처리 (따옴표) 적용 완료
- [x] wrapper 스크립트 (omc-hud.mjs) 존재 확인
- [x] 플러그인 캐시 (v3.3.10) 설치 확인
- [x] HUD 구현 파일들 존재 확인
- [x] stdin 처리 로직 정상 확인
- [x] 수동 테스트 결과 정상 (fallback 메시지는 예상된 동작)

### 🔄 다음 단계

**Claude Code / VSCode 재시작 후**:

1. 상태바에 HUD가 표시되는지 확인
2. 대화를 시작하고 HUD가 업데이트되는지 확인
3. 만약 여전히 안 보이면:
   - Claude Code 로그 확인
   - `/oh-my-claudecode:doctor` 실행
   - 이 문서의 진단 절차 수행

---

## 추가 참고

### OMC 관련 명령어

- `/oh-my-claudecode:omc-setup` - 초기 설정
- `/oh-my-claudecode:doctor` - 진단 도구
- `/oh-my-claudecode:hud setup` - HUD 재설치

### 관련 파일

- 설정: `~/.claude/settings.json`
- 플러그인: `~/.claude/plugins/cache/omc/`
- HUD 스크립트: `~/.claude/hud/omc-hud.mjs`
- 대화 로그: `~/.claude/projects/*/[conversation-id].jsonl`

### 도움말

- oh-my-claudecode GitHub: https://github.com/cyanheads/oh-my-claudecode
- Claude Code 문서: https://docs.anthropic.com/claude/docs/claude-code

---

**문서 종료** - 이 문서 하나로 전체 HUD 컨텍스트 복원 가능