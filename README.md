# Heterarchy Gateway

Forge와 Orchestration의 HTTP 계약을 검증·전달하고 조회 결과를 조합하는 Gateway입니다. 도메인 상태와 Git 작업은 각 backend가 담당합니다.

## 실행

CPython **3.14.7t free-threaded**와 **uv**를 사용합니다.

`module_setting_envs/`의 세 `*_settings.env.example`을 `.example` 없는 이름으로 복사하고 실행 환경에 맞게 설정합니다. 환경변수가 설정 파일보다 우선합니다. [설정 안내](module_setting_envs/README.md)

| 설정 | 로컬 실행 예시 |
| --- | --- |
| `GATEWAY_FORGE_BASE_URL` | `http://127.0.0.1:8797/api/v1` |
| `GATEWAY_ORCHESTRATION_BASE_URL` | `http://127.0.0.1:8798` |

```sh
uv sync --locked --python 3.14.7t
make run
```

Gateway는 `http://127.0.0.1:7979`에서 실행됩니다.

## API

| 기능 | 경로 |
| --- | --- |
| Forge Workspace·Activity·DAG·Swarm | `/forges` |
| Orchestration Profile·Autonomy·Swarm·브리지·SSE | `/orchestrations` |
| Swarm·DAG 조합 조회 | `/mixed` |
| 상태 확인 | `/healthz` |
| 응답 계약 조회·검증 | `/diagnostics/contracts` |

요청·응답 스키마와 전체 경로는 실행 중인 앱에서 확인합니다. [API 문서](http://127.0.0.1:7979/docs) · [OpenAPI](http://127.0.0.1:7979/openapi.json)

- Forge·Orchestration API에는 해당 backend의 `Authorization`을 전달합니다.
- Mixed API에는 `X-Forge-Authorization`과 `X-Orchestration-Authorization`을 모두 전달합니다.
- JSON 필드는 모두 필수이며 nullable 필드에도 명시적 `null`을 전달합니다. GET의 선택 query는 생략할 수 있습니다.
- SSE 재개에는 `Last-Event-ID`를 사용합니다.

## 검증

```sh
make ci
```

런타임·Ruff·Pyrefly·가드레일·전체 테스트를 실행합니다. 비공개 하네스 `.agents/python_bff_harness/`, 인접 Forge checkout, Orchestration `4643381` checkout 및 Rust SSD 빌드 환경이 필요합니다.

실제 3서비스 연동 테스트는 격리된 Forge·Orchestration·Gateway 프로세스와 로컬 worker·broker fixture를 사용합니다.

## 이미지 발행

`pyproject.toml`의 버전과 같은 `vX.Y.Z` Git 태그를 push하면 전체 CI와 컨테이너 실행 검증 후 `ghcr.io/heterarchy-systems/heterarchy-gateway:X.Y.Z`를 Private으로 발행합니다. `latest`도 같은 이미지를 가리킵니다. 발행한 숫자 버전은 재사용하지 않습니다.

`main` push에서는 이미지 빌드·실행을 검증합니다. Private 이미지를 다운로드할 때는 GitHub Packages 읽기 권한으로 GHCR에 로그인합니다.
