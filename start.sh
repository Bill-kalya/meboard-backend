#!/bin/bash
set -euo pipefail

cd backend

# Install Rust if not available
if ! command -v cargo &> /dev/null; then
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
  export PATH="$HOME/.cargo/bin:$PATH"
fi

echo "==> Building Rust backend..."
cargo build --release

echo "==> Starting backend..."
exec ./target/release/meboard-backend
