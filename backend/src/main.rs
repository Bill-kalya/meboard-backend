mod api;
mod db;
mod error;
mod models;
mod services;
mod state;

use std::sync::Arc;

use axum::http::Method;
use tower_http::cors::{Any, CorsLayer};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    dotenvy::dotenv().ok();
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("meboard_backend=debug")),
        )
        .init();

    let database_url = std::env::var("DATABASE_URL").expect("DATABASE_URL must be set");
    let redis_url = std::env::var("REDIS_URL").unwrap_or_else(|_| "redis://127.0.0.1:6379".into());
    let jwt_secret = std::env::var("JWT_SECRET").unwrap_or_else(|_| "meboard-dev-secret-change-me".into());
    let ai_url = std::env::var("AI_SERVICE_URL").unwrap_or_else(|_| "http://localhost:8000".into());
    let port = std::env::var("PORT")
        .ok()
        .and_then(|value| value.parse::<u16>().ok())
        .unwrap_or(8080);

    let pool = db::init_pool(&database_url).await?;
    let redis_client = redis::Client::open(redis_url)?;

    let state = Arc::new(state::AppState {
        pool,
        redis_client,
        jwt_secret,
        ai_url,
    });

    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods([
            Method::GET,
            Method::POST,
            Method::PUT,
            Method::DELETE,
            Method::OPTIONS,
        ])
        .allow_headers(Any);

    let app = api::router(state).layer(cors);
    let listener = tokio::net::TcpListener::bind(("0.0.0.0", port)).await?;
    tracing::info!("MeBoard backend listening on http://{}", listener.local_addr()?);
    axum::serve(listener, app).await?;
    Ok(())
}
