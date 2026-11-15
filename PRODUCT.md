# PRODUCT

Heterarchy는 사용자가 Workspace를 선택하고 그 안의 작업(Activity)과 승인·실행 증거를 확인하는 데스크톱 애플리케이션이다.

## 확인된 목적

- 현재 첫 화면은 **최소 Swift 설정 화면**이다. Workspace 폴더 등록, 실제 등록 수, 기존 도메인 또는 무료 Cloudflare 임시 주소, MCP7979 상태를 우선한다. Activity·승인·실행 증거를 포함하는 확장 GUI는 실제 MCP 기능 검증 이후 단계다.
- 실제 API가 없는 동작은 지원하지 않음을 화면에 명확히 표시한다. 가짜 성공, 숫자 0 채우기, 샘플 데이터를 제품 화면에 넣지 않는다.

## 실행 구조 (확인된 것)

- **데스크톱 앱**: SwiftUI/AppKit 기반 Heterarchy.app. 기존 TypeScript GUI·Tauri·Next.js UI는 제거됐다. TypeScript browser companion은 provider 실행 구성요소로 별도 유지한다. 연동되지 않은 Workbench 시안은 DEBUG 빌드에서만 열 수 있으며 릴리스 첫 화면·탐색 경로에서 제외한다.
- **Gateway**: Python BFF(uv, CPython 3.14.7t + Dishka). 앱이 Gateway의 대체 권한을 갖지 않는다.
- **Forge / Orchestration**: 로컬 네이티브 프로세스. Docker로 옮기지 않는다.
- **Broker**: heterarchy-broker의 공식 Docker Compose 3노드.

## 수명 계약

- 앱 종료는 창/UI만 끝낸다. 앱의 명시적인 MCP 시작·중지 동작은 Gateway owner 명령에 위임하며, GUI 종료 자체는 backend나 실행 작업을 중지하지 않는다.
- Gateway에 연결할 수 없으면 앱은 자체 화면을 열고 조회 실패·재확인 필요 상태를 표시한다. 등록 수를 일부만 확인하면 부분 집계로 표시하고, 확인할 수 없는 값을0이나 정상 상태로 대체하지 않는다. 설정에는 소유 파일 참조를 저장하며 브라우저에는 Source credential을 전달하지 않는다.

## 이번 전환의 경계

- 서명·notarization, 원격 CI, push·배포, Keychain·운영 DB 변경은 포함되지 않았다.
- 기존 전체 E2E 목표와 미구현 backend 계약은 이 전환으로 해결된 것이 아니며 별도 미완료로 유지된다.
