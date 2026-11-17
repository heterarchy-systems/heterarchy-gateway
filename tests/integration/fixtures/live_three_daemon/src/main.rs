use std::collections::BTreeMap;
use std::error::Error;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::net::{Ipv4Addr, SocketAddr, TcpListener as StdTcpListener};
use std::os::unix::fs::OpenOptionsExt;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex as StdMutex};
use std::time::{SystemTime, UNIX_EPOCH};

use forge_control::{
    AgentBindingActivateRequest, AgentBindingReserveRequest, AgentOperationsDelegationRequest,
    CoordinatorClaimRequest, ForgeControl, ForgeControlWorker,
};
use forge_domain::{
    ActivityId, AgentDeclaredRole, AgentDisplayName, AgentInstanceId, AgentSessionId,
    AuthenticatedPrincipal, DirectTokenId, EstablishWorkspace, ForgeBackendId, LocationId,
    LocationRevision, OrchestrationIssuerId, RuntimeInstanceId, TimestampMillis, WorkspaceId,
    WorkspaceRoot,
};
use forge_persistence::{
    AgentBindingActivationRequest, AgentBindingReservationRequest, AgentOperationsFreezeRequest,
    GlobalRegistry, WorkspaceStore,
};
use forge_workspace::{LocationService, WorkspaceStateLayout};
use heterarchy_orchestration_auth::{
    McpTokenCatalog, McpTokenIssueRequest, McpTokenLabel, McpTokenRuntime, McpTokenService,
    McpTokenWorker,
};
use heterarchy_orchestration_backend::{
    AdmissionIssuerBootstrap, BackendConfig, TokenAuthorityBootstrap, forge_source_config, serve,
    session_process::EmbeddedSessionAuthorityConfig,
};
use heterarchy_orchestration_operations::BrokerClusterConfig;
use heterarchy_orchestration_runtime::{OrchestrationRuntime, access::OperatorPolicy};
use heterarchy_orchestration_sessions::SessionCatalogAuthority;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::net::{TcpListener, TcpStream};
use tokio_util::sync::CancellationToken;
use uuid::Uuid;

const TOKEN_PEPPER: [u8; 32] = [0x6B; 32];
const SESSION_FILE_NAME: &str = "agent-sessions.sqlite3";
const TOKEN_FILE_NAME: &str = "operator.token";
const SEED_FILE_NAME: &str = "fixture-seed.json";
const ORCHESTRATION_LISTEN_ENV: &str = "GATEWAY_LIVE_ORCHESTRATION_LISTEN";
const SESSION_AUTHORITY_LISTEN_ENV: &str = "GATEWAY_LIVE_SESSION_AUTHORITY_LISTEN";

type FixtureResult<T = ()> = Result<T, Box<dyn Error>>;

#[derive(Debug, Deserialize, Serialize)]
struct FixtureSeed {
    forge_root: PathBuf,
    orchestration_root: PathBuf,
    forge_config_path: PathBuf,
    forge_source_config_path: PathBuf,
    forge_bearer_path: PathBuf,
    operator_bearer_path: PathBuf,
    session_secret_path: PathBuf,
    operator_principal_id: Uuid,
    workspace_id: Uuid,
    workspace_revision: i64,
    location_id: Uuid,
    location_revision: i64,
    locator: String,
    relative_root: String,
    activity_id: Uuid,
    session_id: Uuid,
    coordinator_agent_id: Uuid,
    outbox_migration_id: Uuid,
    destination_id: Uuid,
    forge_backend_id: Uuid,
    issuer_id: Uuid,
}

#[tokio::main]
async fn main() -> FixtureResult {
    let arguments = std::env::args().skip(1).collect::<Vec<_>>();
    match arguments.as_slice() {
        [command, root] if command == "seed" => {
            let seed = seed(Path::new(root))?;
            println!("{}", serde_json::to_string(&seed)?);
            Ok(())
        }
        [command, root] if command == "serve" => serve_host(Path::new(root)).await,
        _ => Err("usage: gateway-live-three-daemon-host <seed|serve> <fixture-root>".into()),
    }
}

fn seed(root: &Path) -> FixtureResult<FixtureSeed> {
    if !root.is_absolute() {
        return Err("fixture root must be an absolute path".into());
    }
    fs::create_dir_all(root)?;
    let root = root.canonicalize()?;
    let forge_root = root.join("forge");
    let orchestration_root = root.join("orchestration");
    let auth_root = root.join("auth");
    let location_root = forge_root.join("location");
    let workspace_root = location_root.join("workspace-0");
    fs::create_dir_all(&forge_root)?;
    fs::create_dir_all(&orchestration_root)?;
    fs::create_dir_all(&auth_root)?;
    fs::create_dir_all(&workspace_root)?;

    let runtime = OrchestrationRuntime::open(&orchestration_root)?;
    let destination_id = runtime.destination_id();

    let token_catalog = McpTokenCatalog::open(auth_root.join("tokens.sqlite3"))?;
    let (token_client, mut token_worker) =
        McpTokenWorker::start(McpTokenService::new(TOKEN_PEPPER, token_catalog))?;
    let now_ms = unix_time_ms()?;
    let issued = token_client.issue(McpTokenIssueRequest::new(
        McpTokenLabel::new("gateway-live-e2e-operator".to_owned())?,
        TimestampMillis::new(now_ms)?,
    ))?;
    let operator_principal_id = issued.metadata().id().into_uuid();
    let principal =
        AuthenticatedPrincipal::DirectToken(DirectTokenId::from_uuid(operator_principal_id));
    let operator_bearer_path = auth_root.join(TOKEN_FILE_NAME);
    write_private_file(
        &operator_bearer_path,
        format!("Bearer {}\n", issued.reveal().as_str()).as_bytes(),
    )?;
    token_worker.shutdown()?;

    let session_request_id = Uuid::now_v7();
    let session_outcome = runtime.open_session(session_request_id, principal, now_ms)?;
    let session_id = session_outcome.session.session_id;
    let session_catalog_path = orchestration_root.join(SESSION_FILE_NAME);
    let session_authority = SessionCatalogAuthority::new(session_catalog_path);

    let registry_path = forge_root.join("registry.sqlite3");
    let location_id = LocationId::from_uuid(Uuid::now_v7());
    let mut locations = LocationService::new(GlobalRegistry::open(&registry_path)?);
    let location = locations.register_selected_path(
        location_id,
        "gateway-live-e2e".to_owned(),
        &location_root,
        TimestampMillis::new(now_ms)?,
    )?;
    drop(locations);

    fs::write(
        workspace_root.join("README.md"),
        "Gateway live end-to-end baseline\n",
    )?;
    let layout = WorkspaceStateLayout::initialize(&workspace_root)?;
    let workspace_id = WorkspaceId::from_uuid(Uuid::now_v7());
    let establish = EstablishWorkspace::new(
        workspace_id,
        location.id(),
        WorkspaceRoot::from_canonical(layout.workspace_root().to_path_buf())?,
        layout.root_fingerprint()?,
        TimestampMillis::new(now_ms.saturating_add(1))?,
    );
    let mut workspace_store = WorkspaceStore::open(&layout, &establish)?;
    let activity_id = ActivityId::from_uuid(Uuid::now_v7());
    let coordinator_agent_id = AgentInstanceId::from_uuid(Uuid::now_v7());
    let outbox_migration_id = Uuid::now_v7();
    let observed = TimestampMillis::new(now_ms.saturating_add(5))?;
    let freeze = workspace_store.freeze_agent_operations(&AgentOperationsFreezeRequest::new(
        outbox_migration_id,
        destination_id,
        observed,
    )?)?;
    drop(workspace_store);

    let forge_backend_id = Uuid::now_v7();
    let issuer_id = Uuid::now_v7();
    let forge_control = ForgeControl::with_session_authority(
        LocationService::new(GlobalRegistry::open_existing(&registry_path)?),
        Box::new(session_authority),
    );
    let (forge_client, mut forge_worker) = ForgeControlWorker::start(forge_control)?;
    let location_revision = LocationRevision::INITIAL;
    let locator = forge_client
        .workspace_discover(location_id, location_revision)?
        .into_iter()
        .find(|entry| entry.display_name() == "workspace-0")
        .ok_or("seeded Forge workspace was not discoverable")?
        .locator()
        .clone();
    let scope = forge_client.resolve_workspace(location_id, location_revision, locator)?;
    let workspace_revision = scope.workspace_revision().get();
    let now = TimestampMillis::new(now_ms.saturating_add(10))?;
    let _activity = forge_client.bootstrap_activity(
        scope.clone(),
        activity_id,
        RuntimeInstanceId::from_uuid(Uuid::now_v7()),
        now,
        TimestampMillis::new(now.get().saturating_add(600_000))?,
    )?;

    let request_id = Uuid::now_v7();
    let reservation = AgentBindingReservationRequest::new(
        request_id,
        activity_id,
        coordinator_agent_id,
        AgentSessionId::from_uuid(session_id),
        principal,
        TimestampMillis::new(now.get().saturating_add(1))?,
    )?;
    let _reservation = forge_client.reserve_agent_binding(AgentBindingReserveRequest {
        scope: scope.clone(),
        freeze: freeze.clone(),
        reservation,
        observed_at: TimestampMillis::new(now.get().saturating_add(2))?,
    })?;
    let delegation = forge_client.delegate_agent_operations(AgentOperationsDelegationRequest {
        scope: scope.clone(),
        freeze,
        manifest_digest: [0xE7; 32],
        observed_at: TimestampMillis::new(now.get().saturating_add(3))?,
    })?;
    let activation = AgentBindingActivationRequest::new(
        request_id,
        [0xE8; 32],
        AgentDisplayName::new("gateway-live-e2e-coordinator".to_owned())?,
        AgentDeclaredRole::new("coordinator".to_owned())?,
        forge_domain::AgentTransportKind::StreamableHttp,
    )?;
    let _activation = forge_client.activate_agent_binding(AgentBindingActivateRequest {
        scope: scope.clone(),
        delegation,
        activation,
        session_id: AgentSessionId::from_uuid(session_id),
        principal,
        observed_at: TimestampMillis::new(now.get().saturating_add(4))?,
    })?;
    let _claim = forge_client.activity_coordinator_claim(CoordinatorClaimRequest {
        session_id: AgentSessionId::from_uuid(session_id),
        scope: scope.clone(),
        activity_id,
        agent_id: coordinator_agent_id,
        principal,
        observed_at: TimestampMillis::new(now.get().saturating_add(5))?,
    })?;
    forge_worker.shutdown()?;

    let forge_address = loopback_address("GATEWAY_LIVE_FORGE_ADDR")?;
    let session_authority_address = loopback_address(SESSION_AUTHORITY_LISTEN_ENV)?;
    let forge_bearer_path = auth_root.join("forge-api.token");
    let session_secret_path = auth_root.join("forge-session-authority.token");
    write_private_file(
        &forge_bearer_path,
        format!("gateway-live-forge-{}\n", Uuid::now_v7()).as_bytes(),
    )?;
    write_private_file(
        &session_secret_path,
        format!("gateway-live-session-authority-{}\n", Uuid::now_v7()).as_bytes(),
    )?;

    let forge_config_path = forge_root.join("forge-backend.json");
    let forge_config = serde_json::json!({
        "listen": forge_address.to_string(),
        "registry_path": registry_path,
        "product_cache_root": forge_root.join("product-cache"),
        "backend_id": forge_backend_id,
        "issuer_id": issuer_id,
        "destination_id": destination_id,
        "api_bearer_file": forge_bearer_path,
        "session_authority": session_authority_address.to_string(),
        "session_bearer_file": session_secret_path,
        "rust_ci": null
    });
    write_private_file(
        &forge_config_path,
        serde_json::to_string_pretty(&forge_config)?.as_bytes(),
    )?;

    let forge_source_config_path = orchestration_root.join("forge-source.json");
    let forge_source_config = serde_json::json!({
        "address": forge_address.to_string(),
        "bearer_file": forge_bearer_path,
        "scopes": [],
        "effect_facts": {
            "backend_id": forge_backend_id,
            "destination_id": destination_id
        }
    });
    write_private_file(
        &forge_source_config_path,
        serde_json::to_string_pretty(&forge_source_config)?.as_bytes(),
    )?;

    let seed = FixtureSeed {
        forge_root,
        orchestration_root,
        forge_config_path,
        forge_source_config_path,
        forge_bearer_path,
        operator_bearer_path,
        session_secret_path,
        operator_principal_id,
        workspace_id: scope.workspace_id().into_uuid(),
        workspace_revision,
        location_id: scope.locator().location_id().into_uuid(),
        location_revision: scope.locator().expected_revision().get(),
        locator: scope.locator().encode(),
        relative_root: scope
            .locator()
            .relative_root()
            .to_string_lossy()
            .into_owned(),
        activity_id: activity_id.into_uuid(),
        session_id,
        coordinator_agent_id: coordinator_agent_id.into_uuid(),
        outbox_migration_id,
        destination_id,
        forge_backend_id,
        issuer_id,
    };
    write_private_file(
        root.join(SEED_FILE_NAME),
        serde_json::to_string_pretty(&seed)?.as_bytes(),
    )?;
    Ok(seed)
}

async fn serve_host(root: &Path) -> FixtureResult {
    let root = root.canonicalize()?;
    let seed_path = root.join(SEED_FILE_NAME);
    let seed: FixtureSeed = serde_json::from_slice(&fs::read(&seed_path)?)?;
    let orchestration_address = loopback_address(ORCHESTRATION_LISTEN_ENV)?;
    let session_authority_address = loopback_address(SESSION_AUTHORITY_LISTEN_ENV)?;
    let broker_listener = TcpListener::bind((Ipv4Addr::LOCALHOST, 0)).await?;
    let broker_address = broker_listener.local_addr()?;
    let operations_guard = StdTcpListener::bind((Ipv4Addr::LOCALHOST, 0))?;
    let broker_operations_address = operations_guard.local_addr()?;
    let broker_cluster =
        BrokerClusterConfig::from_single_node(broker_address, broker_operations_address)?;
    let broker_owners = Arc::new(StdMutex::new(BTreeMap::new()));
    let cancellation = CancellationToken::new();
    let broker_task = tokio::spawn(serve_fixture_broker(
        broker_listener,
        Arc::clone(&broker_owners),
        cancellation.child_token(),
    ));

    let token_catalog = McpTokenCatalog::open(root.join("auth/tokens.sqlite3"))?;
    let (token_client, token_worker) =
        McpTokenWorker::start(McpTokenService::new(TOKEN_PEPPER, token_catalog))?;
    let token_runtime = McpTokenRuntime::from_parts(token_client, token_worker);
    let coordinator_authority = forge_source_config::load(&seed.forge_source_config_path)?;
    let operator_principal =
        AuthenticatedPrincipal::DirectToken(DirectTokenId::from_uuid(seed.operator_principal_id));
    let operator_policy = OperatorPolicy::new(vec![operator_principal])?;
    let session_authority = EmbeddedSessionAuthorityConfig::new(
        session_authority_address,
        seed.orchestration_root.join(SESSION_FILE_NAME),
        seed.session_secret_path.clone(),
    )?;
    let worker_bearer_path = seed.operator_bearer_path.clone();
    let config = BackendConfig::new(orchestration_address, seed.orchestration_root.clone())?
        .with_token_authority(TokenAuthorityBootstrap::Runtime(token_runtime))
        .with_operator_policy(operator_policy)
        .with_coordinator_authority(coordinator_authority)
        .with_admission_issuer(AdmissionIssuerBootstrap::new(
            OrchestrationIssuerId::from_uuid(seed.issuer_id),
            ForgeBackendId::from_uuid(seed.forge_backend_id),
            60_000,
        )?)
        .with_broker_cluster(broker_cluster)
        .with_worker_bearer_file(worker_bearer_path)
        .with_embedded_session_authority(session_authority);

    println!("ORCHESTRATION_FIXTURE_STARTING");
    std::io::stdout().flush()?;
    let backend_result = serve_until_signal(config, cancellation.clone()).await;
    cancellation.cancel();
    broker_task.await??;
    drop(operations_guard);
    backend_result
}

async fn serve_until_signal(
    config: BackendConfig,
    cancellation: CancellationToken,
) -> FixtureResult {
    let mut server = tokio::spawn(serve(config, cancellation.clone()));
    let mut terminate = tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())?;
    tokio::select! {
        result = &mut server => result??,
        signal = tokio::signal::ctrl_c() => {
            signal?;
            cancellation.cancel();
            server.await??;
        }
        _ = terminate.recv() => {
            cancellation.cancel();
            server.await??;
        }
    }
    Ok(())
}

type BrokerSessionOwners = Arc<StdMutex<BTreeMap<String, (u64, String)>>>;

async fn serve_fixture_broker(
    listener: TcpListener,
    owners: BrokerSessionOwners,
    cancellation: CancellationToken,
) -> std::io::Result<()> {
    loop {
        tokio::select! {
            _ = cancellation.cancelled() => return Ok(()),
            accepted = listener.accept() => {
                let (socket, _) = accepted?;
                let connection_owners = Arc::clone(&owners);
                tokio::spawn(async move {
                    let _ = handle_fixture_broker_connection(socket, &connection_owners).await;
                });
            }
        }
    }
}

async fn handle_fixture_broker_connection(
    socket: TcpStream,
    owners: &BrokerSessionOwners,
) -> std::io::Result<()> {
    let (read_half, mut write_half) = socket.into_split();
    let mut reader = BufReader::new(read_half);
    let mut line = String::new();
    if reader.read_line(&mut line).await? == 0 {
        return Ok(());
    }
    let Ok(envelope) = serde_json::from_str::<Value>(&line) else {
        return Ok(());
    };
    let Some(reply) = evaluate_fixture_broker_frame(&envelope, owners) else {
        return Ok(());
    };
    let mut encoded = serde_json::to_vec(&reply)
        .map_err(|error| std::io::Error::new(std::io::ErrorKind::InvalidData, error))?;
    encoded.push(b'\n');
    write_half.write_all(&encoded).await?;
    write_half.flush().await?;
    write_half.shutdown().await
}

fn evaluate_fixture_broker_frame(envelope: &Value, owners: &BrokerSessionOwners) -> Option<Value> {
    let request_id = envelope.get("request_id")?.as_str()?;
    let operation = envelope.get("operation")?.as_str()?;
    match operation {
        "acquire_command_session_owner" => {
            let session_id = envelope.get("command_session_id")?.as_str()?;
            let expected_epoch = envelope.get("expected_owner_epoch")?.as_u64()?;
            let instance_id = envelope.get("owner_instance_id")?.as_str()?;
            let mut guard = owners.lock().ok()?;
            let next_epoch = match guard.get(session_id).cloned() {
                None => {
                    guard.insert(
                        session_id.to_owned(),
                        (expected_epoch, instance_id.to_owned()),
                    );
                    Some(expected_epoch)
                }
                Some((current_epoch, current_instance))
                    if current_instance == instance_id && current_epoch == expected_epoch =>
                {
                    Some(current_epoch)
                }
                Some((current_epoch, _)) if current_epoch == expected_epoch => {
                    let advanced = current_epoch.saturating_add(1);
                    guard.insert(session_id.to_owned(), (advanced, instance_id.to_owned()));
                    Some(advanced)
                }
                Some(_) => None,
            };
            drop(guard);
            Some(match next_epoch {
                Some(epoch) => serde_json::json!({
                    "version": 3,
                    "request_id": request_id,
                    "ok": true,
                    "result": { "owner_epoch": epoch },
                }),
                None => serde_json::json!({
                    "version": 3,
                    "request_id": request_id,
                    "ok": false,
                    "error": {
                        "code": "STALE_FENCE",
                        "message": "expected owner epoch mismatch",
                        "disposition": "rejected",
                    },
                }),
            })
        }
        "authority.record" => {
            let revision = envelope.get("revision")?.as_u64()?;
            Some(serde_json::json!({
                "version": 3,
                "request_id": request_id,
                "ok": true,
                "result": { "recorded_revision": revision },
            }))
        }
        _ => None,
    }
}

fn loopback_address(environment_name: &str) -> FixtureResult<SocketAddr> {
    let raw = std::env::var(environment_name)?;
    let address = raw.parse::<SocketAddr>()?;
    if !address.ip().is_loopback() || address.port() == 0 {
        return Err(format!("{environment_name} must be a nonzero loopback address").into());
    }
    Ok(address)
}

fn unix_time_ms() -> FixtureResult<i64> {
    let millis = SystemTime::now().duration_since(UNIX_EPOCH)?.as_millis();
    let result = i64::try_from(millis)?;
    Ok(result)
}

fn write_private_file(path: impl AsRef<Path>, contents: &[u8]) -> FixtureResult {
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(0o600)
        .open(path)?;
    file.write_all(contents)?;
    file.sync_all()?;
    Ok(())
}
