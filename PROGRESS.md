# SpriteForge MCP 進捗

基準日: 2026-11-28（`develop`）
Obsidianに本プロジェクトの `TODO.md`・`STATUS.md` は未作成のため、現時点では本書を進捗正本とします。

## 残りの作業（優先度順）

1. 実クライアントからのツール呼び出し確認（着手中）: 登録は確認済み。`auth-shell` で開いたPowerShellからClaude Code・Codexを起動し、`get_version` を呼び出せることを確認する。2026-11-28のヘッドレス確認は、Claude CLIのOAuth期限切れとCodexの設定モデル `gpt-6.1-sol` が利用不可のため、ツール呼び出し前に失敗した。また同日、Claude Desktop（Code）セッションからの接続は `Authorization` ヘッダー拒否（HTTP 401）となった（`auth-shell` 外で起動したため環境変数のトークンが渡っていない可能性が高い。未確定）。
2. プロジェクト管理機能: DB（永続ストア）の導入。`doctor` のDB項目が未実装表示。
3. 永続ジョブ管理: `jobs_available: false` を解消し、ジョブ登録・状態取得・キャンセルを実装（2に依存）。
4. 画像生成Provider: ピクセルアート・アニメーション生成のMCP Tool群とProvider接続（2・3に依存）。現在のToolは `get_version` のみ。
5. 画像書き出し: 透明PNG・スプライトシート／アトラス出力（4に依存）。
6. 安全な更新適用: `update download`（検証付き保存）と `update apply`（インストール・復旧）、トレイの更新操作の有効化。
7. 配布: WiX ToolsetベースのMSI作成（現状は `dist/` にwheel・sdistのみ）。
8. Obsidianへ `TODO.md`・`STATUS.md` を作成し、横断TODOの正本を移す。

## 完了済み

- CLIによるDaemon管理（start/status/stop、PID再利用）、診断用STDIO、トレイアプリ（a8017cf）
- 認証付きHTTP接続、クライアント設定 configure/unconfigure、auth-shell（d467ba9）
- 設定・コマンド・MCP接続・安全性・依存関係の文書（日英）
- `develop` のGitHubへのpush（2026-11-28、018b6e9）
- テスト分離（2026-11-28）: テスト時だけMutex名前空間を分離（`SPRITEFORGE_TEST_MUTEX_NAMESPACE`、`tests/conftest.py`）。本番の「データ保存先によらずセッションで1つ」の仕様は維持
- 実ユーザー設定への登録確認（2026-11-28）: `~/.claude.json`・`~/.codex/config.toml` に所有情報付きで登録済み（`configure --dry-run` で競合なし）

## 検証状況（2026-11-28）

- `uv run pytest -q`: 50 passed（実Daemon稼働中に実行、実Daemonは継続稼働）
- `uv run ruff check src tests`: All checks passed
- Daemon起動後、トークンありで `claude mcp get spriteforge-mcp` が `Connected`、トークンなしでHTTP 401拒否
- `codex mcp get spriteforge-mcp`: Streamable HTTPの登録内容を表示（接続自体の確認は未了）

## 進捗率

約20%（基盤：Daemon・認証・クライアント設定・HTTP接続は完了。中核機能のDB・ジョブ・画像生成・書き出し、更新、配布が未着手）。
現在フェーズ「基盤・接続確立」: 約95%（残りは実クライアントからのツール呼び出し確認のみ）。
算定根拠: 上記残作業1〜7に対し、基盤部分の完了を工数比で概算した推測値です。
