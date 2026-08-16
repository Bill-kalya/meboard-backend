use axum::extract::{Path, State};
use axum::Json;
use serde_json::json;
use uuid::Uuid;

use crate::error::AppResult;
use crate::models::{BoardNode, CreateNodeRequest, UpdateNodeRequest};
use crate::services::{get_board_owner, get_node, publish_event};
use crate::state::SharedState;

pub async fn list(
    Path(board_id): Path<Uuid>,
    State(state): State<SharedState>,
) -> AppResult<Json<Vec<BoardNode>>> {
    let nodes = sqlx::query_as::<_, BoardNode>(
        "SELECT * FROM nodes WHERE board_id = $1 ORDER BY z, created_at",
    )
    .bind(board_id)
    .fetch_all(&state.pool)
    .await?;
    Ok(Json(nodes))
}

pub async fn create(
    Path(board_id): Path<Uuid>,
    State(state): State<SharedState>,
    Json(request): Json<CreateNodeRequest>,
) -> AppResult<Json<BoardNode>> {
    get_board_owner(&state, board_id).await?;

    let id = Uuid::new_v4();
    let node = sqlx::query_as::<_, BoardNode>(
        "INSERT INTO nodes (id, board_id, node_type, content, x, y, z, width, height, rotation, style, semantic)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
         RETURNING *",
    )
    .bind(id)
    .bind(board_id)
    .bind(&request.node_type)
    .bind(&request.content)
    .bind(request.x)
    .bind(request.y)
    .bind(request.z.unwrap_or(0.0))
    .bind(request.width.unwrap_or(200.0))
    .bind(request.height.unwrap_or(100.0))
    .bind(request.rotation.unwrap_or(0.0))
    .bind(request.style.clone().unwrap_or_else(|| json!({})))
    .bind(request.semantic.clone())
    .fetch_one(&state.pool)
    .await?;

    publish_event(
        &state,
        board_id,
        "node_created",
        &json!({ "node_id": id.to_string() }),
    )
    .await;

    Ok(Json(node))
}

pub async fn update(
    Path(node_id): Path<Uuid>,
    State(state): State<SharedState>,
    Json(request): Json<UpdateNodeRequest>,
) -> AppResult<Json<BoardNode>> {
    let existing = get_node(&state, node_id).await?;

    let node = sqlx::query_as::<_, BoardNode>(
        "UPDATE nodes
         SET content = COALESCE($1, content),
             x = COALESCE($2, x),
             y = COALESCE($3, y),
             z = COALESCE($4, z),
             width = COALESCE($5, width),
             height = COALESCE($6, height),
             rotation = COALESCE($7, rotation),
             style = COALESCE($8, style),
             updated_at = now()
         WHERE id = $9
         RETURNING *",
    )
    .bind(request.content)
    .bind(request.x)
    .bind(request.y)
    .bind(request.z)
    .bind(request.width)
    .bind(request.height)
    .bind(request.rotation)
    .bind(request.style)
    .bind(node_id)
    .fetch_one(&state.pool)
    .await?;

    publish_event(
        &state,
        existing.board_id,
        "node_updated",
        &json!({ "node_id": node_id.to_string() }),
    )
    .await;

    Ok(Json(node))
}

pub async fn delete(
    Path(node_id): Path<Uuid>,
    State(state): State<SharedState>,
) -> AppResult<Json<serde_json::Value>> {
    let node = get_node(&state, node_id).await?;
    sqlx::query("DELETE FROM nodes WHERE id = $1")
        .bind(node_id)
        .execute(&state.pool)
        .await?;

    publish_event(
        &state,
        node.board_id,
        "node_deleted",
        &json!({ "node_id": node_id.to_string() }),
    )
    .await;

    Ok(Json(json!({ "ok": true })))
}
