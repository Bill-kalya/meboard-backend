use axum::extract::{Path, State};
use axum::Json;
use uuid::Uuid;

use crate::error::{AppError, AppResult};
use crate::models::AnalyzeNodeRequest;
use crate::services::get_node;
use crate::state::SharedState;

async fn ai_client() -> Result<reqwest::Client, AppError> {
    Ok(reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .map_err(|e| AppError::Internal(format!("http client: {e}")))?)
}

pub async fn analyze(
    Path(board_id): Path<Uuid>,
    State(state): State<SharedState>,
    Json(request): Json<AnalyzeNodeRequest>,
) -> AppResult<Json<serde_json::Value>> {
    let node = get_node(&state, request.node_id).await?;
    if node.board_id != board_id {
        return Err(AppError::BadRequest("node does not belong to board".to_string()));
    }

    let payload = serde_json::json!({
        "node_id": node.id.to_string(),
        "node_type": node.node_type,
        "content": node.content,
        "style": node.style,
    });

    let client = ai_client().await?;
    let response = client
        .post(format!("{}/analyze", state.ai_url))
        .json(&payload)
        .send()
        .await
        .map_err(|e| AppError::Upstream(format!("ai-service unreachable: {e}")))?;

    if !response.status().is_success() {
        return Err(AppError::Upstream(format!(
            "ai-service returned {}",
            response.status()
        )));
    }
    let profile: serde_json::Value = response
        .json()
        .await
        .map_err(|e| AppError::Upstream(format!("bad ai-service response: {e}")))?;

    sqlx::query("UPDATE nodes SET semantic = $1, updated_at = now() WHERE id = $2")
        .bind(&profile)
        .bind(node.id)
        .execute(&state.pool)
        .await?;

    Ok(Json(profile))
}

pub async fn relationships(
    Path(board_id): Path<Uuid>,
    State(state): State<SharedState>,
) -> AppResult<Json<serde_json::Value>> {
    let cache_key = format!("relationships:{}", board_id);

    let mut redis_connection = match state.redis_client.get_multiplexed_async_connection().await {
        Ok(connection) => Some(connection),
        Err(_) => None,
    };

    if let Some(connection) = redis_connection.as_mut() {
        let cached: Option<String> = redis::cmd("GET")
            .arg(&cache_key)
            .query_async(connection)
            .await
            .unwrap_or(None);
        if let Some(value) = cached {
            if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(&value) {
                return Ok(Json(parsed));
            }
        }
    }

    let nodes = sqlx::query_as::<_, crate::models::BoardNode>(
        "SELECT * FROM nodes WHERE board_id = $1",
    )
    .bind(board_id)
    .fetch_all(&state.pool)
    .await?;

    let briefs: Vec<serde_json::Value> = nodes
        .iter()
        .map(|node| {
            serde_json::json!({
                "id": node.id.to_string(),
                "type": node.node_type,
                "content": node.content,
                "style": node.style,
            })
        })
        .collect();

    let client = ai_client().await?;
    let response = client
        .post(format!("{}/relationships", state.ai_url))
        .json(&serde_json::json!({ "nodes": briefs }))
        .send()
        .await
        .map_err(|e| AppError::Upstream(format!("ai-service unreachable: {e}")))?;

    let body: serde_json::Value = response
        .json()
        .await
        .map_err(|e| AppError::Upstream(format!("bad ai-service response: {e}")))?;

    if let Some(connection) = redis_connection.as_mut() {
        let _: redis::RedisResult<()> = redis::cmd("SETEX")
            .arg(&cache_key)
            .arg(60)
            .arg(body.to_string())
            .query_async(connection)
            .await;
    }

    Ok(Json(body))
}
