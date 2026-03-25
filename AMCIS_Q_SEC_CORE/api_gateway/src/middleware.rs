// Gateway middleware for authentication and authorization

use axum::{
    extract::Request,
    http::StatusCode,
    middleware::Next,
    response::{IntoResponse, Response},
};
use std::sync::Arc;

/// JWT validation middleware
pub async fn jwt_auth<B>(
    request: Request,
    next: Next,
) -> Response {
    // TODO: Implement JWT validation
    // For now, pass through
    next.run(request).await
}

/// Rate limiting middleware
pub async fn rate_limit<B>(
    request: Request,
    next: Next,
) -> Response {
    // TODO: Implement rate limiting with DashMap or similar
    // For now, pass through
    next.run(request).await
}

/// Request ID injection middleware
pub async fn request_id<B>(
    mut request: Request,
    next: Next,
) -> Response {
    let request_id = uuid::Uuid::new_v4().to_string();
    
    request.headers_mut().insert(
        "x-request-id",
        request_id.parse().unwrap(),
    );
    
    next.run(request).await
}
