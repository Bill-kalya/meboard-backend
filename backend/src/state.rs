use std::sync::Arc;

use sqlx::PgPool;

pub struct AppState {
    pub pool: PgPool,
    pub redis_client: redis::Client,
    pub jwt_secret: String,
    pub ai_url: String,
}

pub type SharedState = Arc<AppState>;
