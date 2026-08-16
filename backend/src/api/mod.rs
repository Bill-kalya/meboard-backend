pub mod auth;
pub mod boards;
pub mod nodes;
pub mod search;
pub mod semantics;
pub mod ws;

use std::sync::Arc;

use axum::response::IntoResponse;
use axum::routing::{get, post, put};
use axum::Json;
use axum::Router;
use serde_json::json;

use crate::state::AppState;

pub async fn health() -> axum::response::Response {
    Json(json!({ "status": "ok", "service": "meboard-backend" })).into_response()
}

pub fn router(state: Arc<AppState>) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/api/auth/register", post(auth::register))
        .route("/api/auth/login", post(auth::login))
        .route("/api/boards", get(boards::list).post(boards::create))
        .route(
            "/api/boards/{id}",
            get(boards::get).put(boards::update).delete(boards::delete),
        )
        .route(
            "/api/boards/{id}/nodes",
            get(nodes::list).post(nodes::create),
        )
        .route("/api/nodes/{id}", put(nodes::update).delete(nodes::delete))
        .route("/api/boards/{id}/analyze", post(semantics::analyze))
        .route(
            "/api/boards/{id}/relationships",
            get(semantics::relationships),
        )
        .route("/api/boards/{id}/search", get(search::search))
        .route("/ws", get(ws::handler))
        .with_state(state)
}
