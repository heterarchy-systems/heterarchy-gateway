# [DEPRECATED] Heterarchy Gateway

> **⚠️ DEPRECATED (사용 중단)**
>
> 이 저장소(`heterarchy-gateway`)는 **Deprecated** 처리되어 더 이상 유지보수하거나 사용하지 않습니다.
> 도메인 상태·권한·영속성을 소유하는 `heterarchy-orchestration`과 `heterarchy-forge`는 각각 독립된 순수 Rust 헤드리스 백엔드 데몬으로 운영되며, 기존 Chrome 브라우저 컴패니언 및 Python BFF 게이트웨이 계층은 아키텍처 단순화에 따라 폐기되었습니다.

---

Forge와 Orchestration의 공개 backend 계약을 HTTP/MCP 경계에서 전달하는 BFF입니다. 도메인 상태·권한·영속성은 backend에 남습니다. 현재 전체 제품 이관을 완료하지 않았으며 [준비 상태 감사](docs/backend-readiness-2026-10-04.md)에 실제 source 계약과 blocker를 기록했습니다.

Python은 **CPython 3.14.7 free-threaded**, DI는 **Dishka 1.10.1**입니다. 최신 사용자 요청에 따라 일반 Python 정책을 갱신했고, 잠긴 의존성 import 및 실제 앱 startup/shutdown 뒤 GIL disabled를 확인합니다. dependency-injector와 orjson은 제거했고 JSON은 검증된 typed codec을 사용합니다.

Python 환경·설치·실행은 **uv만** 사용합니다. pip, python -m pip, uv pip는 사용하지 않습니다. 정확한 interpreter는 .python-version, 재현 가능한 Python dependency graph는 uv.lock이 소유합니다. 데스크톱 GUI는 dependency 없는 SwiftUI/AppKit 앱이며 `native/GatewayDesktop`에서 빌드합니다.

설정은 [shared/settings_modules](app/shared/settings_modules)에 나눕니다. `base_settings.py`는 공통 pydantic-settings 정책, `orchestration_settings.py`와 `forge_settings.py`는 각 backend origin·고정 API 경로, `gateway_settings.py`는 모듈 조합과 worker 자원 정책을 관리합니다. 서버 origin은 `GATEWAY_ORCHESTRATION_BASE_URL`, `GATEWAY_FORGE_BASE_URL`로 지정합니다. root가 설정을 호출기에 전달하며 source와 다른 경로는 거부합니다.

```sh
uv python install 3.14.7t
make sync
make ci
make native-app
make run
```

CI의 공통 진입점은 `make ci`입니다. [.github/workflows/ci.yml](.github/workflows/ci.yml)은 trusted main push와 main 수동 실행에서 같은 실제 검사들을 실행합니다. 공개 저장소에 비공개 하네스를 넣지 않으므로 별도의 CI 하네스 공급이 필요합니다. 현재 원격 workflow·secrets·실행 상태와 설정 전제는 [CI 안내](docs/ci.md)에 구분했습니다. 로컬 검사 통과를 원격 CI 성공으로 보고하지 않습니다.

`make ci`는 Swift contract/build 검사를 실행한 뒤 Python runtime·typing·회귀 검사를 이어 실행합니다. 로컬 검증을 실제 backend 인증 연동으로 확대하지 않습니다.

기존 React/Vite/Tauri control panel과 Chrome browser companion은 제거했습니다. Swift 앱은 Workspace 등록, 실제 Workspace 수, 선택적 기존 hostname 또는 빈 domain의 임시 tunnel 설정, MCP 7979 시작·중지·상태와 실제 pending consent를 제공합니다. 모든 명령은 Gateway의 `desktop` owner entry를 별도 process로 실행하며 직접 backend HTTP나 credential 입력을 사용하지 않습니다.

GUI의 새 Workspace 등록은 폴더 이름을 사용한 ChatGPT Project 자동 생성·연결로 이어집니다. 기존 Workspace는 중복 생성하지 않습니다. [설정 및 복구 절차](docs/workspace-chatgpt-project.md)에 준비 조건을 정리했으며, Source 권한 설정, 실제 브라우저 접근, Project 안의 에이전트 실행은 각각 별도 증거로 확인합니다.

Swift 앱은 기본적으로 `~/.config/heterarchy-gateway/desktop.json`을 사용합니다. 별도 로컬 검증 환경은 앱 실행 시 `GATEWAY_DESKTOP_CONFIG`에 절대 경로를 지정합니다. 빈 값·상대 경로는 거부하며 기존 설정으로 돌아가 다른 runtime을 제어하지 않습니다. 설정의 소유권과 credential/catalog 검사는 Gateway owner가 동일하게 적용합니다.

make run은 loopback 127.0.0.1:8799, asyncio/h11, 한 worker, concurrency 100으로 실행합니다. /healthz는 이 gateway의 liveness만 표시합니다. /readyz나 전체 backend 준비를 성공으로 표시하는 가짜 endpoint는 없습니다. 기본 설정에서는 backend domain route를 노출하지 않습니다.

[로컬 Container 실행 안내](docs/local-container.md)에 Dockerfile·Compose와 실제 Linux arm64 검증 결과를 기록했습니다. 비root·읽기전용 이미지에서 GUI와 no-GIL 기동은 확인했으며 현재 Docker Desktop의 Mac host 접근 및 실제 backend 인증 통합은 미완료입니다. CI workflow는 `make container-config`도 호출합니다.

확인한 Orchestration Session 읽기 경로를 연결하려면 operator가 실제 loopback backend origin을 지정합니다.

```sh
GATEWAY_ORCHESTRATION_BASE_URL=http://127.0.0.1:8798 make run
```

GET /api/v1/orchestration/sessions/{session_id}는 요청에서 전달받은 인증을 backend에 넘기며, 최종 principal/Session 소유권 검증은 Orchestration이 수행합니다. 설정된 origin은 literal loopback만 허용하고 URL credential/path/query/fragment를 금지합니다. shared client 기본 credential/cookie를 요청의 authority로 사용하지 않습니다. 알려진 request identity와 source-shaped response를 검사하고 자동 재시도하지 않습니다.

같은 Orchestration origin에서 [Workspace Team 목록·단건 조회](docs/team-read.md)도 연결합니다. 목록 limit과 truncated, 선택 Session header, backend-owned Workspace 읽기 권한을 보존하고 단건 absence는 source 그대로 `200 null`을 반환합니다. Gateway가 operator나 Session membership을 생성하지 않습니다.

[Leadership·Team 구성원 읽기](docs/governance-read.md)는 같은 backend 권한과 optional Session selector를 사용합니다. Leadership의 nullable view·cursor history, backend deadline 판단과 Team 참여 목록의 원본 revision·시간·정렬을 유지합니다. 투표·리뷰·진행·확정·복구의 mutation/read 계약은 아래 거버넌스 MCP 검증에 추가됐으며, 실제 참여자 준비·선거·handoff E2E는 별도로 확인합니다.

[Agent Profile 목록·단건 조회](docs/profile-read.md)는 전역 bearer catalog 계약을 유지합니다. 목록은 기본64 및 최대64의 배열이고, 단건 부재는 `404 NOT_FOUND`입니다. Team의 Workspace·Session 권한을 이 전역 조회에 추가하지 않습니다.

Forge Location 목록은 실제 Forge origin을 `GATEWAY_FORGE_BASE_URL`에 설정한 경우에만 `GET /api/v1/forge/locations?request_id=<UUID>`로 노출합니다. incoming bearer는 Forge API credential이며 Orchestration 토큰과 동일시하지 않습니다. 공개 읽기 요청을 source의 `POST /api/v1/commands/location.list`와 빈 payload로 전달하고, 최대 100개의 Location ID·이름·revision·state만 반환합니다. 비공개 root와 timestamp 또는 임의 pagination은 추가하지 않습니다. source가 허용하는 nil UUID도 보존합니다.

Forge 응답의 request ID·API version·성공 flag·오류 code/status를 검증합니다. parse 전 인증 실패의 nil correlation을 구분하고, 인증 실패는 공개 401로 전달합니다. `UNKNOWN_OUTCOME`은 공개 202와 retryable=false로 반환하며 자동 재제출하지 않습니다. 오류 응답은 caller의 request ID를 유지하고 backend 내부 message·recovery hint를 노출하지 않습니다. 현재 검증은 실제 앱·Dishka와 mock backend 계약이며 Forge 실서비스 연결을 의미하지 않습니다.

[Forge Workspace inventory](docs/workspace-inventory.md)는 Location ID와 revision fence를 요구하는 보호된 읽기로 연결합니다. 원본 registered/unavailable 행과 Workspace 등록 필드를 유지하며 등록·활성화는 수행하지 않습니다.

[Forge Activity 목록·단건 읽기](docs/activity-read.md)도 보호된 Workspace scope에서 제공합니다. 원본 locator 형식, revision, lease 상태와 단건 부재의 `200/activity:null`을 보존하고 lifecycle 재시도 권한을 추가하지 않습니다.

[Forge Queue 관찰](docs/queue-observations.md)은 전역 상태, Workspace runtime과 저장 설정을 전달합니다. 저장값과 실제 적용값을 분리하고 원본의 비원자 관찰 의미를 유지합니다. 상태 관찰이 설정 저장·즉시 적용·재시도 허가를 뜻하지 않습니다.

[Forge Goal·DAG·assignment 읽기](docs/forge-plan-reads.md)는 네 source command를 HTTP/MCP로 연결합니다. 부재의 found=false, 저장된 DAG 출력 순서와 서로 다른 revision fence를 보존합니다. 실제 Forge 인증 통합은 아직 미검증입니다.

[Forge 검증 상태 조회](docs/verification-projection.md)는 명령별 최신 running·passed·failed와 원본 disposition을 전달합니다. 검증을 실행하거나 실행 권한을 부여하지 않습니다.

[Forge Diff 목록·inventory](docs/diff-read.md)는 전체 evidence metadata와 요약 metadata를 분리해 제공합니다. 두 API의 nil 허용 차이, 원본의 100개 한도와 nullable payload를 유지하며 artifact content·health를 추가하지 않습니다.

[Diff 본문·artifact health](docs/diff-artifact-read.md)는 verified content와 현재 health를 분리해 전달합니다. 두 operation은 최대 256-entry full evidence 때문에 고정 4 MiB consumer cap을 사용합니다. Read의 빈 본문·128 KiB UTF-8 byte 한도와 doctor에 source scope echo·content·has-content가 없다는 차이를 유지합니다.

[Writer Lease 단건·목록 관찰](docs/writer-lease-read.md)은 만료됐지만 해제되지 않은 lease, source 관찰 시각, nullable Session과 64/4 scope 페이지를 유지합니다. 조회를 갱신·복구 권한으로 바꾸지 않습니다.

[실행 evidence 관찰](docs/execution-observation.md)은 issuer inventory와 bounded output ledger를 제공합니다. 현재 Goal selection과 historical provenance를 구분하고 실행·재시도·grant를 만들지 않습니다. Inventory는 source limit256에 맞춘 고정4MiB, observe는1MiB 한도를 사용합니다.

Session, Forge Location·Workspace inventory·Activity·Queue·Goal·DAG·assignment·검증 상태·Diff, Team·구성원·Leadership 및 Profile 조회를 [MCP 어댑터](docs/mcp-read.md)에서도 사용합니다. MCP는 기본 비활성이며 실제 issuer/resource와 검증기가 필요합니다. 명시적 local OAuth 설정과 private credential profile을 사용하면 root가 실제 발급·검증 경로를 구성합니다. 설정된 backend와 승인된 scope의 도구만 노출합니다. Team 생성과 정확한 조회는 아래 협업 명령 검증에 추가됐으며 실제 참여자 협업 성공은 별도 증거가 필요합니다.

[MCP 데스크톱 검증](docs/mcp-desktop-verification-2026-10-07.md)에서 트레이·독립 설정 창·MCP 시작/중지/재시작, 실제 OAuth와 native backend 읽기 결과를 확인할 수 있습니다. 전체 ChatGPT 협업 E2E와 public HTTPS 연결은 아직 완료되지 않았습니다.

[협업 명령 검증](docs/mcp-cooperation-verification-2026-10-07.md)에는 Team 생성·정확한 조회, AgentRequest admit·recover의 등록과 로컬 실행 증거를 기록했습니다. 변경 도구에는 `gateway.write`와 개별 작업 scope가 모두 필요하며, 불확정 결과는 자동 재시도 없이 정확한 readback 입력을 반환합니다. 공개 연결 설정은 `.env.example`의 opt-in 항목을 사용합니다. 공개 모드는 native owner 승인과 private OAuth client catalog가 필요하며, 실제 ChatGPT 연결 성공과 도메인 협업 성공은 별도로 확인합니다.

[공개 MCP 준비 검증](docs/public-mcp-verification-2026-10-07.md)은 HTTPS metadata, public 경로 차단, 클라이언트 등록 영속화, 실제 native 승인과 로컬 TCP 결과를 다룹니다. Cloudflare 목적지 변경은 아직 저장 전이며 외부 ChatGPT 성공으로 해석하지 않습니다.

[거버넌스 MCP 검증](docs/governance-mcp-verification-2026-10-07.md)에는 투표·리뷰·발언·리더 진행·확정·복구의 10개 경로를 기록했습니다. 로컬 계약과 SDK 검증은 통과했으며 실제 선거와 리더 교체는 source 권한·참여자·시간 조건을 갖춘 별도 E2E로 확인해야 합니다.

[Provider-worker 검증](docs/provider-worker-verification-2026-10-07.md)은 Orchestration의 15개 operator API 호출기와 기존 OAuth 등록을 보존하는 읽기 범위 갱신을 다룹니다. 공용 HTTP pool은 환경 프록시를 사용하지 않아 loopback용 source credential이 프록시로 전달되지 않습니다.

기본 upstream 전체 deadline은 10초(설정 최대 60초), 기본 응답 cap은 1 MiB입니다. Source-valid bounded response가 더 큰 일부 operation에는 [응답 예산 호환성](docs/response-budget-compatibility.md)에 기록한 exact fixed cap을 적용합니다. 이것은 per-response/worker 정책이며 여러 backend의 전체 처리량·성능이나 global distributed admission 보장이 아닙니다. backend가 실제로 실행 중이지 않으면 조회는 unavailable로 실패합니다. 인증정보 생성·운영 restart·DB 변경을 자동 수행하지 않습니다.

Dishka async container/client는 한 worker의 한 event loop에서만 사용합니다. OS-thread/loop 사이 공유와 get_sync를 금지합니다. request 의존성을 병렬 fanout 전에 해석하고 typed instance를 전달합니다. APP client는 lifespan의 finally에서 닫히고 request child는 ASGI 요청 종료/취소 시 정리됩니다. mutable request/auth/scope를 APP state나 공용 header에 저장하지 않습니다. 이 검증은 Dishka의 모든 사용법에 대한 일반적인 free-threading 인증이 아닙니다.

Ruff는 py314, correctness/import/async/FastAPI/security/typing을 검사하고 unsafe fix는 사용하지 않습니다. Pyrefly는 strict이며 missing import를 Any로 치환하지 않습니다. 소유한 app과 tests에서 Any·object·Protocol 타입을 예외 없이 금지합니다. 검사 적용 코드는 app/shared/guardrails/에서 .agents/의 하네스 설정·출처·guard 정의를 읽습니다. Pydantic은 kwargs 없는 completion hook을 사용하고, deferred model도 factory 금지를 우회할 수 없도록 검증합니다.

```sh
make runtime    # direct/native imports + actual startup/shutdown no-GIL
make lint       # formatting and lint
make typecheck  # strict types
make guards     # canonical harness guards with Gateway policy
make test       # focused contract/lifecycle regression tests
```

기존 strict/frozen/default-factory 거부와 source guard scope/predicate는 회귀로 보존했습니다. diagnostics는 명시적 public contract/store를 받는 factory이며 default 앱에 mount하지 않습니다. 실제 계약이나 참조가 없던 example.com 기반 Forge/workflow/task 호출기 3개는 제거했습니다. 등록된 실제 읽기 계약만 source와 설정에서 관리합니다.

개발 전 [기능별 실행 계획](docs/plans/00-readiness-and-execution-2026-10-04.md)과 [Forge Location 읽기 계획](docs/plans/04-forge-location-read-2026-10-05.md)을 Alexandria에 저장·read-back했습니다. [계약 ledger](docs/backend-contract-ledger.md)에서 source·mock·실서비스 증거를 구분합니다. Forge 전체 read/mutation, MCP parity, Workspace/SSE recovery와 실제 backend integration은 아직 별도 gate입니다. 하네스 전체 machine-contract binding과 배포 완료를 source/style 테스트만으로 주장하지 않습니다.

도서관 원문과 provenance는 private .agents/에 보관합니다. [Dishka container/scopes](https://dishka.readthedocs.io/en/stable/container/), [FastAPI integration](https://dishka.readthedocs.io/en/stable/integrations/fastapi.html), [uv interpreter 선택](https://docs.astral.sh/uv/concepts/python-versions/), [Ruff 설정](https://docs.astral.sh/ruff/configuration/), [Pyrefly 설정](https://pyrefly.org/en/docs/configuration/)을 설정 근거로 참고했습니다.


개발 전 [.agents/DEVELOPMENT_RULES.md](.agents/DEVELOPMENT_RULES.md)를 읽습니다. 기능 모듈은 `schemas/`, `routers/`와 오류 계약을 위한 `exceptions/`로 구성합니다. Session 모델은 `schemas/session_schemas.py`, 라우트는 `routers/session_routers.py`, 기능별 타입 별칭은 `schemas/types/session_types.py`, 오류 응답은 `exceptions/session_exceptions.py`에 둡니다. API 호출·설정·자원 기반은 `app/shared/`가 소유합니다. 관련 작은 클래스는 합칠 수 있으며 모든 기능을 한 파일에 몰지 않습니다. Any/object/Protocol 타입을 금지하고, 모델 필드는 `Annotated[타입, described_field(...)]`, 라우터 상태 값은 FastAPI status 상수로 선언합니다. `make bff-rules`는 구조·타입·import·registry·조건부 route inventory를 검사하며 문서의 모든 규칙을 자동 증명하는 것은 아닙니다.

[응답 예산 호환성](docs/response-budget-compatibility.md)에 source 최대응답과 operation별 소비자 한도를 기록했습니다. Goal 목록8MiB·DAG12MiB·Team 목록4MiB·Diff inventory2MiB, Diff read·doctor4MiB와 execution inventory4MiB를 각각 고정 설정으로 전달합니다. Global 기본값, unresolved full Diff list, execution observe와 그 밖의 audited operation은1MiB를 유지합니다. Full Diff list는 source pagination/aggregate 계약이 없으므로 모든 유효한 응답을 지원한다는 전체 이관 증거는 아직 없습니다.

[Forge source 파일 목록](docs/forge-source-file-list.md)은 exact Workspace·Activity와 nested native directory를 source `file.list`에 전달합니다. HTTP GET과 MCP `forge_files_list`가 같은 typed caller를 사용하고, source default512 entries/64KiB native path bytes, no-follow classification·raw-name order·truncation을 보존합니다. Runtime ID·관찰 시각을 ownership/heartbeat 권한으로 해석하거나 Gateway에서 파일을 직접 읽지 않습니다. 실제 Forge 인증 연결은 별도 미검증입니다.

[Forge source 내용·텍스트 검색](docs/forge-source-slice-search.md)은 exact Activity/Workspace에서 UTF-8 line slice와literalquery를읽습니다. Slice의모든줄hash를유지하도록고정12MiB consumer cap을사용하고, search/file.list/global1MiB는유지합니다. Whole-file EOL·final-newline과fragment를혼동하지않고, 검색native path·zero-based line-digit·preview bytebudget과source traversal/truncation을보존합니다. 같은typedcaller를HTTP/MCP에연결했고공통오류는source exceptions에모았습니다.


현재 일곱 화면은 지원되는 HTTP read 13종에 연결돼 있습니다. Forge/O token은 페이지 메모리에만 공급하며 disconnect/pagehide에서 비웁니다. Location을 읽고 선택하면 해당 revision의 Workspace 목록을 선택할 수 있습니다. Orchestration Workspace는 별도 입력하며 Forge Workspace와 자동 동일시하지 않습니다. [화면 연결과 실제 검증 범위](docs/handoffs/glm/main-screen-wiring-2026-10-06.md), [후속 GLM 업무](docs/handoffs/glm/next-wave-2026-10-06.md)를 참고합니다.

Activity 선택 및 AgentRequest/Approval 화면 통합을 완료했습니다. [BFF 실행 검증](docs/handoffs/glm/main-g21-g22-integration-2026-10-06.md)은 실제 Gateway와 명시적 mock upstream을 TCP로 연결하고 브라우저까지 확인한 증거입니다. 실제 Rust backend 인증 연동 증거와 구분합니다.
