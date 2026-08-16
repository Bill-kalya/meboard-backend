use uuid::Uuid;

use crate::error::AppError;
use crate::models::BoardNode;
use crate::state::AppState;

pub async fn publish_event(
    state: &AppState,
    board_id: Uuid,
    event: &str,
    data: &serde_json::Value,
) {
    let mut connection = match state.redis_client.get_multiplexed_async_connection().await {
        Ok(connection) => connection,
        Err(_) => return,
    };
    let payload = serde_json::json!({
        "event": event,
        "board_id": board_id.to_string(),
        "data": data,
    })
    .to_string();
    let _: redis::RedisResult<()> = redis::cmd("PUBLISH")
        .arg(format!("board:{board_id}"))
        .arg(&payload)
        .query_async(&mut connection)
        .await;
}

pub async fn get_node(state: &AppState, node_id: Uuid) -> Result<BoardNode, AppError> {
    let node = sqlx::query_as::<_, BoardNode>("SELECT * FROM nodes WHERE id = $1")
        .bind(node_id)
        .fetch_optional(&state.pool)
        .await?
        .ok_or_else(|| AppError::NotFound(format!("node {node_id}")))?;
    Ok(node)
}

pub async fn get_board_owner(state: &AppState, board_id: Uuid) -> Result<uuid::Uuid, AppError> {
    let owner_id = sqlx::query_scalar::<_, uuid::Uuid>("SELECT owner_id FROM boards WHERE id = $1")
        .bind(board_id)
        .fetch_optional(&state.pool)
        .await?
        .ok_or_else(|| AppError::NotFound(format!("board {board_id}")))?;
    Ok(owner_id)
}
