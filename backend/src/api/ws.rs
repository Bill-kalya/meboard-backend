use axum::extract::ws::{Message, WebSocket, WebSocketUpgrade};
use axum::extract::{Query, State};
use axum::response::IntoResponse;
use futures::{SinkExt, StreamExt};
use serde::Deserialize;
use uuid::Uuid;

use crate::state::SharedState;

#[derive(Debug, Deserialize)]
pub struct WsQuery {
    pub board_id: Option<Uuid>,
}

pub async fn handler(
    ws: WebSocketUpgrade,
    Query(query): Query<WsQuery>,
    State(state): State<SharedState>,
) -> impl IntoResponse {
    ws.on_upgrade(move |socket| handle_socket(socket, state, query.board_id))
}

async fn handle_socket(socket: WebSocket, state: SharedState, board_id: Option<Uuid>) {
    let channel = match board_id {
        Some(id) => format!("board:{id}"),
        None => "board:*".to_string(),
    };

    let mut pubsub = match state.redis_client.get_async_pubsub().await {
        Ok(pubsub) => pubsub,
        Err(e) => {
            tracing::warn!("redis pubsub unavailable: {e}");
            return;
        }
    };
    if pubsub.subscribe(&channel).await.is_err() {
        return;
    }
    let mut incoming = pubsub.on_message();

    let (mut sink, mut client_stream) = socket.split();
    let mut publisher = match state.redis_client.get_multiplexed_async_connection().await {
        Ok(connection) => Some(connection),
        Err(_) => None,
    };

    loop {
        tokio::select! {
            client_message = client_stream.next() => {
                match client_message {
                    Some(Ok(Message::Text(text))) => {
                        if let Some(connection) = publisher.as_mut() {
                            let _: redis::RedisResult<()> = redis::cmd("PUBLISH")
                                .arg(&channel)
                                .arg(text.to_string())
                                .query_async(connection)
                                .await;
                        }
                    }
                    Some(Ok(Message::Close(_))) | None => break,
                    _ => {}
                }
            }
            redis_message = incoming.next() => {
                if let Some(message) = redis_message {
                    if let Ok(payload) = message.get_payload() {
                        if sink.send(Message::Text(payload)).await.is_err() {
                            break;
                        }
                    }
                }
            }
        }
    }
}
