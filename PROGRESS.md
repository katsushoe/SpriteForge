# SpriteForge MCP 進捗

基準日: 2026-11-28（`develop` / `d467ba9`）
Obsidianに本プロジェクトの `TODO.md`・`STATUS.md` は未作成のため、現時点では本書を進捗正本とします。

## 残りの作業（優先度順）

1. 実クライアント接続確認: Claude Code・Codexの実ユーザー設定へ `configure` で登録し、`auth-shell` 経由で対話接続できることを確認する（MCP_SETUP: 未完了・未確認）。
2. `develop` のpush: 2コミット（`a8017cf`, `d467ba9`）が未push、追跡ブランチ未設定。
3. プロジェクト管理機能: DB（永続ストア）の導入。`doctor` のDB項目が未実装表示。
4. 永続ジョブ管理: `jobs_available: false` を解消し、ジョブ登録・状態取得・キャンセルを実装（3に依存）。
5. 画像生成Provider: ピクセルアート・アニメーション生成のMCP Tool群とProvider接続（3・4に依存）。現在のToolは `get_version` のみ。
6. 画像書き出し: 透明PNG・スプライトシート／アトラス出力（5に依存）。
7. 安全な更新適用: `update download`（検証付き保存）と `update apply`（インストール・復旧）、トレイの更新操作の有効化。
8. 配布: WiX ToolsetベースのMSI作成（現状は `dist/` にwheel・sdistのみ）。
9. Obsidianへ `TODO.md`・`STATUS.md` を作成し、横断TODOの正本を移す。

## 完了済み

- CLIによるDaemon管理（start/status/stop、PID再利用）、診断用STDIO、トレイアプリ（a8017cf）
- 認証付きHTTP接続、クライアント設定 configure/unconfigure、auth-shell（d467ba9）
- 設定・コマンド・MCP接続・安全性・依存関係の文書（日英）

## 検証状況（2026-11-28）

- `uv run pytest -q`: 49 passed
- `uv run ruff check src tests`: All checks passed

## 進捗率

約20%（基盤：Daemon・認証・クライアント設定は完了。中核機能のDB・ジョブ・画像生成・書き出し、更新、配布が未着手）。
算定根拠: 上記残作業1〜8に対し、基盤部分の完了を工数比で概算した推測値です。
