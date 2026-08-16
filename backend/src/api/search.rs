use axum::extract::{Path, Query, State};
use axum::Json;
use serde::Deserialize;
use uuid::Uuid;

use crate::error::AppResult;
use crate::models::BoardNode;
use crate::state::SharedState;

#[derive(Debug, Deserialize)]
pub struct SearchQuery {
    pub q: String,
}

pub async fn search(
    Path(board_id): Path<Uuid>,
    Query(query): Query<SearchQuery>,
    State(state): State<SharedState>,
) -> AppResult<Json<Vec<BoardNode>>> {
    let nodes = sqlx::query_as::<_, BoardNode>(
        "SELECT * FROM nodes
         WHERE board_id = $1
           AND (content::text ILIKE '%' || $2 || '%'
                OR COALESCE(semantic::text, '') ILIKE '%' || $2 || '%')
         ORDER BY updated_at DESC
         LIMIT 50",
    )
    .bind(board_id)
    .bind(&query.q)
    .fetch_all(&state.pool)
    .await?;
    Ok(Json(nodes))
}
