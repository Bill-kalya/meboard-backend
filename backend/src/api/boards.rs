use axum::extract::{Path, State};
use axum::http::HeaderMap;
use axum::Json;
use serde_json::json;
use uuid::Uuid;

use crate::error::AppResult;
use crate::models::{Board, CreateBoardRequest, UpdateBoardRequest};
use crate::services::get_board_owner;
use crate::state::SharedState;

use super::auth::user_from_headers;

pub async fn list(
    State(state): State<SharedState>,
    headers: HeaderMap,
) -> AppResult<Json<Vec<Board>>> {
    let owner_id = user_from_headers(&headers, &state.jwt_secret)?;
    let boards = sqlx::query_as::<_, Board>(
        "SELECT * FROM boards WHERE owner_id = $1 ORDER BY updated_at DESC",
    )
    .bind(owner_id)
    .fetch_all(&state.pool)
    .await?;
    Ok(Json(boards))
}

pub async fn create(
    State(state): State<SharedState>,
    headers: HeaderMap,
    Json(request): Json<CreateBoardRequest>,
) -> AppResult<Json<Board>> {
    let owner_id = user_from_headers(&headers, &state.jwt_secret)?;
    let id = Uuid::new_v4();
    let board = sqlx::query_as::<_, Board>(
        "INSERT INTO boards (id, name, owner_id, view_state) VALUES ($1, $2, $3, $4) RETURNING *",
    )
    .bind(id)
    .bind(&request.name)
    .bind(owner_id)
    .bind(json!({}))
    .fetch_one(&state.pool)
    .await?;
    Ok(Json(board))
}

pub async fn get(
    Path(board_id): Path<Uuid>,
    State(state): State<SharedState>,
    headers: HeaderMap,
) -> AppResult<Json<Board>> {
    let owner_id = user_from_headers(&headers, &state.jwt_secret)?;
    let board = sqlx::query_as::<_, Board>("SELECT * FROM boards WHERE id = $1 AND owner_id = $2")
        .bind(board_id)
        .bind(owner_id)
        .fetch_optional(&state.pool)
        .await?
        .ok_or(crate::error::AppError::NotFound(format!("board {board_id}")))?;
    Ok(Json(board))
}

pub async fn update(
    Path(board_id): Path<Uuid>,
    State(state): State<SharedState>,
    headers: HeaderMap,
    Json(request): Json<UpdateBoardRequest>,
) -> AppResult<Json<Board>> {
    let owner_id = user_from_headers(&headers, &state.jwt_secret)?;
    let current = get_board_owner(&state, board_id).await?;
    if current != owner_id {
        return Err(crate::error::AppError::Unauthorized);
    }

    let board = sqlx::query_as::<_, Board>(
        "UPDATE boards
         SET name = COALESCE($1, name),
             view_state = COALESCE($2, view_state),
             updated_at = now()
         WHERE id = $3
         RETURNING *",
    )
    .bind(request.name)
    .bind(request.view_state)
    .bind(board_id)
    .fetch_one(&state.pool)
    .await?;
    Ok(Json(board))
}

pub async fn delete(
    Path(board_id): Path<Uuid>,
    State(state): State<SharedState>,
    headers: HeaderMap,
) -> AppResult<Json<serde_json::Value>> {
    let owner_id = user_from_headers(&headers, &state.jwt_secret)?;
    let current = get_board_owner(&state, board_id).await?;
    if current != owner_id {
        return Err(crate::error::AppError::Unauthorized);
    }

    sqlx::query("DELETE FROM boards WHERE id = $1")
        .bind(board_id)
        .execute(&state.pool)
        .await?;
    Ok(Json(json!({ "ok": true })))
}
