# Heterarchy Gateway

포트 **7979**에서 Forge와 Orchestration의 실제 HTTP 계약을 검증하고 조합하는 Schema Contract Factory입니다. 도메인 상태 전이, 권한 판정, Git 작업과 영속성은 각 backend가 담당합니다.

## 실행

CPython **3.14.7t free-threaded**와 **Dishka 1.10.1**을 사용합니다. Python 실행과 잠긴 의존성 해석은 uv를 사용합니다.

처음 설정할 때 `module_setting_envs/`의 세 `*_settings.env.example`을 대응하는 `*_settings.env`로 복사하고 실제 실행 환경의 값을 입력합니다. 기존 설정 파일은 유지합니다. 각 모델은 자기 모듈의 env 파일과 process 환경변수를 읽으며 process 값이 우선합니다. root `.env`는 Docker Compose 보간용입니다.

| 설정 | 로컬 backend 예시 |
| --- | --- |
| `GATEWAY_FORGE_BASE_URL` | `http://127.0.0.1:8797/api/v1` |
| `GATEWAY_ORCHESTRATION_BASE_URL` | `http://127.0.0.1:8798` |
| Gateway bind | `127.0.0.1:7979` |

Forge base URL은 `/api/v1`을 포함하고 Orchestration base URL은 origin만 받습니다. 설정은 URL 자격증명, query, fragment와 다른 API prefix를 거부합니다.

```sh
make ci
make run
```

`make run`은 `uv run --locked --python 3.14.7t uvicorn app.bootstrap:create_app --factory`를 asyncio/h11, 한 worker, concurrency 100으로 실행합니다. HTTP client와 Dishka container는 worker의 같은 event loop에서 사용하고 lifespan 종료 시 닫습니다.

## 공개 계약

| 표면 | 작업 수 | Gateway prefix |
| --- | --- | --- |
| Forge Workspace·Activity·DAG·Swarm commands | 13 | `/forges` |
| Orchestration Profile | 6 | `/orchestrations/profiles` |
| Orchestration Autonomy | 10 | `/orchestrations/workspaces` |
| Orchestration Native Swarm | 20 | `/orchestrations/workspaces/{workspace_id}/swarms` |
| East-West 브리지 | 3 | `/orchestrations/workspaces/{workspace_id}` |
| Workspace SSE stream | 1 | `/orchestrations/workspaces/{workspace_id}/events` |
| 두 backend 합성 조회 | 2 | `/mixed/workspaces/{workspace_id}` |

실제 method, path와 JSON Schema는 실행 중인 앱의 `/docs`와 `/openapi.json`에서 확인합니다. `/healthz`는 Gateway liveness를 반환합니다.

Forge는 `forge_api`, `request_id`, `op`, `payload`를 가진 versioned command envelope를 받습니다. 현재 DAG 조회 operation은 `dag.read_current`입니다. 다음은 Location 목록 요청입니다.

```json
{
  "forge_api": 1,
  "request_id": "11111111-1111-1111-1111-111111111111",
  "op": "location.list",
  "payload": {}
}
```

이 body를 `POST /forges/locations/list`에 전달합니다. `request_id`는 caller가 선택한 논리 요청 identity로 유지합니다. Forge 응답의 `202 UNKNOWN_OUTCOME`은 오류 envelope와 readback 정보를 보존합니다. Gateway는 요청을 자동 재제출하지 않습니다.

Profile과 Swarm 생성은 원천의 신규 `201`과 replay `200`을 보존합니다. Profile 목록은 root array입니다. 구조화된 `409` 결과와 일반 backend 오류는 각각 해당 계약으로 검증합니다. 손상된 성공 응답은 sanitized `502`, timeout은 `504`로 반환합니다.

## 인증과 입력

전용 Forge·Orchestration route에는 해당 backend의 `Authorization`을 전달합니다. Mixed에는 `X-Forge-Authorization`과 `X-Orchestration-Authorization`을 각각 필수로 전달합니다. 요청 자격증명은 request-scoped caller에 보관합니다.

JSON body와 응답의 모든 필드는 required입니다. nullable 필드도 키와 명시적 `null`을 입력합니다. Source가 합법적으로 생략하는 응답 필드는 DTO parser에서 명시적 null로 정규화합니다. GET query의 `BaseFilter`만 선택 키 생략을 지원합니다. 필수 query 누락, 중복 키와 알 수 없는 query 키는 `422`를 반환합니다.

FastAPI 경계는 strict/frozen Pydantic, 내부 command/result는 기본값 없는 frozen/slotted/keyword-only dataclass와 closed total TypedDict를 사용합니다. 큰 순수 목록 변환에는 순서가 보존되는 bounded `threaded_map`을 사용합니다.

## Mixed 조회

### Swarm overview

`GET /mixed/workspaces/{workspace_id}/swarms/{swarm_run_id}/overview`는 Orchestration inspection과 Forge settlement 조회를 병렬로 수행합니다. 다음 query는 필수입니다.

| Query | Caller가 제공하는 값 |
| --- | --- |
| `forge_request_id` | Forge command 요청 UUID |
| `workspace_revision` | 관측한 Forge Workspace revision |
| `location_id` | Forge Location UUID |
| `expected_revision` | 관측한 Location revision |
| `relative_root` | 해당 Location 아래 Workspace 상대 경로 |

Workspace와 Swarm identity는 path에서 가져옵니다. Locator와 revision은 caller가 관측한 값을 그대로 사용합니다.

선택 query `run_state`는 Orchestration의 canonical run state와 일치하는 결과를 선택합니다. `settled_only=true`는 Forge receipt가 있고 journal state가 `applied`인 결과를 선택합니다. `false`와 생략은 정산 상태를 제한하지 않습니다. 필터 불일치는 trace와 함께 `404`를 반환합니다.

### DAG governance overview

`POST /mixed/workspaces/{workspace_id}/dags/governance-overview`는 완전한 Forge `dag.read_current` command와 governance 조회 키 `goalId`·`dagRevision`을 받습니다. body의 `forge_request`에는 완전한 Forge command를, `governance_query`에는 `goalId`와 `dagRevision`을 전달합니다. 두 키는 모두 필수입니다. Forge scope의 Workspace와 path, 두 Goal identity를 호출 전에 대조합니다.

응답은 Forge current DAG와 요청 revision의 Orchestration governance를 함께 담습니다. 두 read는 독립 시점 관측이며 각각의 revision을 응답에 유지합니다.

두 Mixed route는 요청 의존성을 해결한 후 `TaskGroup`에서 두 read를 실행합니다. 한 의존성의 실패는 sibling 취소와 join 후 원천 HTTP 상태·오류·readback을 포함하는 typed failure로 반환합니다. 두 backend가 함께 실패하면 Forge 상태를 외부 HTTP 상태로 선택하고, 수집된 모든 원천 상태와 오류를 failures 배열에 보존합니다. 전체 요청 deadline은 Gateway runtime timeout을 사용하며 Gateway-owned 504로 반환합니다.

## 전송 예산과 진단

일반 backend 응답 cap은 1 MiB입니다. Native Swarm은 요청 128 KiB, 응답 2 MiB를 적용합니다. 초과 요청은 업스트림 전송 전에 `413`, 초과 응답은 `502`로 반환합니다. Dispatch deadline은 `min(max(runtime timeout, startup + execution + termination + 5초), 900초)`이며 전체 exchange와 HTTPX phase timeout에 함께 적용합니다. 응답 stream은 성공·거부·취소 시 정리합니다.

`GET /diagnostics/contracts`는 실제 53 backend 작업과 2개 Mixed 조합의 response schema를 operation identity로 제공합니다. `POST /diagnostics/contracts/{contract}/validate`는 해당 response contract를 검증합니다. Mixed 응답의 `X-Trace-ID`로 `GET /diagnostics/traces/{trace_id}`에서 bounded in-memory trace를 조회합니다.

개발용 `X-BFF-Failure`는 `GATEWAY_FAILURE_SIMULATION_ENABLED=true`일 때 사용합니다. 비활성 상태의 주입 요청은 `403`입니다. 진단 trace에는 backend payload가 포함됩니다.

## East-West 브리지와 실시간 이벤트

Orchestration이 Forge 호출과 정산 projection을 소유하는 세 경로를 제공합니다.

- `POST /orchestrations/workspaces/{workspace_id}/swarms/{swarm_run_id}/forge-converge`
- `POST /orchestrations/workspaces/{workspace_id}/swarms/{swarm_run_id}/forge-settle`
- `POST /orchestrations/workspaces/{workspace_id}/autonomy-outbox/sync`

브리지 body의 Source 기본값 필드도 required이며 nullable 키는 명시적 null을 입력합니다. 응답은 원천 HTTP 상태와 run·settlement·outbox identity를 검증합니다. Outbox sync의 선택 limit은 null 또는 1부터 64까지이며 mutation으로 등록합니다.

Dispatch body에서 `forgeSessionId`에 유효한 Orchestration session UUID를 주고 `defaultWorktreePath`에 빈 문자열을 전달하면 Source가 해당 Forge session으로 격리 worktree를 준비하고 clean exit 결과를 자동 캡처합니다. 전체 필수 body는 `/docs`의 `DispatchSwarmTurnRequest`에서 확인합니다.

`GET /orchestrations/workspaces/{workspace_id}/events`는 요청 Authorization과 선택 `Last-Event-ID`, `X-Orchestration-Session-Id`를 Source에 전달합니다. 일반 프레임은 `event: state_changed`, `id: epoch:sequence`와 7개 필드의 camelCase JSON data를 사용합니다. cursor는 SSE id로 관리합니다. 재동기화 프레임은 `event: resync_required`, `retry: 2000`, `{reason,currentEpoch,lastDeliveredSequence}` data 뒤 종료됩니다. 이벤트 종류 23개와 실제 Source resync reason을 strict schema로 검증합니다.

SSE는 별도 request-owned HTTP client를 사용합니다. queue는 64개, frame은 16 KiB, queued wire bytes는 1 MiB로 제한하며 downstream send deadline은 30초입니다. Source의 15초 keepalive에 맞춰 read phase timeout은 45초를 사용합니다. 연결·write·pool timeout은 Gateway runtime 설정을 적용합니다. Source admission 실패는 SSE 헤더를 시작하기 전에 원래 JSON 상태와 `Retry-After`를 반환합니다.

## 실제 3-데몬 테스트

```sh
uv run --locked --python 3.14.7t python -m pytest tests/integration/test_live_three_daemon_e2e.py -q
```

테스트는 격리된 Forge 실행 파일 프로세스, Orchestration Source fixture-host 프로세스, Gateway uvicorn 프로세스를 사용합니다. Gateway 포트는 7979이며 Profile·Scope·Swarm·Worker/Verifier·Dispatch·브리지·정산·Mixed·SSE의 HTTP 흐름을 Gateway로 호출합니다. 초기 registry·session·coordinator는 테스트 소유 Rust 도구가 canonical Source API로 준비합니다.

macOS의 stock Orchestration CLI 인증 경로가 사용자 HOME에 고정돼 있어 fixture-host는 Source가 제공하는 token/runtime 주입 API로 격리된 인증 저장소를 사용합니다. 실제 production serving·도메인 코드를 실행하며 테스트 전용 broker protocol fixture와 로컬 codex 실행 파일 fixture를 사용합니다. 외부 AI provider 실행과 stock CLI의 사용자 인증 저장소 발견은 검증 범위에서 별도로 구분합니다.

Rust fixture는 인접 Forge·Orchestration checkout과 지정 SSD를 사용합니다. build/cache/temp는 `/Users/imhaneul/Documents/herterarchy/.codex/rust-ssd` 정책으로 `/Volumes/256.SSD/RustBuild`에 배치하고 실제 Git worktree는 그 밖의 테스트 scratch에 생성합니다. 테스트는 자신이 시작한 프로세스를 소유하고 종료합니다.

## 기능별 코드 구성

스키마는 `{모듈}_{기능}_schema.py`, 기능 라우터는 `{모듈}_{기능}_routers.py`로 관리합니다. 작은 최상위 router는 prefix·인증 metadata와 child router 연결을 담당합니다.

```text
app/orchestration/
  schema/
    autonomy/    orchestration_autonomy_*_schema.py
    swarm/       orchestration_swarm_*_schema.py
    profile/     orchestration_profile_schema.py
    execution/   orchestration_execution_schema.py
    forge_bridge/orchestration_forge_bridge_schema.py
    realtime/    orchestration_realtime_event_schema.py
    types/
  routers/
    autonomy/    orchestration_autonomy_routers.py
    swarm/       orchestration_swarm_*_routers.py
    profile/     orchestration_profile_routers.py
    forge_bridge/orchestration_forge_bridge_routers.py
    realtime/    orchestration_realtime_routers.py

app/forge/
  schema/       envelope/, location/, workspace/, activity/, dag/, swarm/
  routers/      workspace/, dag/, swarm/
```

`swarm/` 스키마는 실제 계약 책임에 따라 identity·workspace·capture·convergence·settlement로 묶습니다. 카탈로그와 private HARNESS의 contract 경로도 해당 기능 모듈을 직접 참조합니다.

FastAPI 상태별 응답 metadata는 공통 `ResponseModelDefinition`·`ResponseContentDefinition`과 closed TypedDict를 사용해 선언합니다. Forge·Orchestration의 공통 오류 집합과 Mixed의 각 view별 집합을 라우터에서 재사용합니다. 실제 HTTP 본문은 기존 Pydantic 응답 모델로 검증합니다. 프로젝트 함수·Application 호출은 keyword 인자로 매개변수의 의미를 명시합니다.

실시간 wire 이름은 `StrEnum`, 바이트·개수·시간 예산은 `IntEnum`이 소유합니다. 기존 Python 타입이나 DTO 필드를 다시 문자열로 적던 중복 marker는 실제 타입·필드 참조로 정리했습니다. 원본 guard가 요구하는 Queue 생성자의 양수 literal `64`는 Enum 예산과의 일치 및 byte-budget 곱을 회귀로 검사합니다.

## 검증

```sh
uv run --locked --python 3.14.7t python -c "import sys; assert sys.version_info[:3] == (3, 14, 7) and not sys._is_gil_enabled()"
uv run --locked --python 3.14.7t ruff format --check app tests
uv run --locked --python 3.14.7t ruff check app tests
uv run --locked --python 3.14.7t pyrefly check
uv run --locked --python 3.14.7t python .agents/python_bff_harness/guardrails/guardrail_runner.py app
uv run --locked --python 3.14.7t python -m pytest tests -q
make ci
```

단위 계약은 ASGI·MockTransport 회귀로, 실제 루프백 업무 흐름은 위 3-데몬 테스트로 검증합니다. 외부 AI provider 실행, stock Orchestration CLI의 사용자 인증 저장소 발견, 원격 CI와 배포는 별도 검증 범위입니다. Container 구성 검사는 `make container-config`로 실행합니다.

개발 규칙은 `.agents/DEVELOPMENT_RULES.md`, 단계별 구현 계획은 `docs/plans/00-master-architecture-and-rules.md`부터 `06-east-west-bridge-sse-and-live-3daemon-e2e.md`까지 적용합니다. private 하네스는 `.agents/python_bff_harness/`에서 공급합니다.
