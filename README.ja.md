# SpriteForge MCP

[English](README.md) | 日本語

Windows 10/11の通常ユーザーで動作する、ピクセルアート・アニメーション向けMCPサーバーです。
現在はCLIによるDaemon管理、認証付きHTTP接続、診断用STDIO、トレイアプリ、クライアント設定の開発版です。
画像生成、プロジェクト管理、永続ジョブ、画像書き出しは未実装です。

## 開発環境

WindowsのPowerShellで、このリポジトリを開いて実行します。Python 3.11以上とuvが必要です。

```powershell
uv sync --locked
uv run spriteforge --help
uv run ruff check src tests
uv run pytest -q
```

`uv.lock` が直接・間接依存のバージョンを固定します。
初回の `uv sync` はPyPIから依存を取得します。

## 起動・停止

同じPowerShellで次を実行します。管理者権限は不要です。

```powershell
uv run spriteforge start
uv run spriteforge status
uv run spriteforge stop
```

`start` と `status` のJSON出力で `state` が `running`、`stop` で `stopped` なら成功です。
既定のMCP接続先は `http://127.0.0.1:8765/mcp` です。
`start` の再実行は同じPIDを返します。CLI終了後もDaemonは動作を続けます。

## トレイアプリ

```powershell
uv run spriteforge tray
```

Windows通知領域のSpriteForgeアイコンから、Daemonの起動・停止・再起動を操作できます。
`Exit Tray` はDaemonを停止しません。停止も必要なら `Exit and Stop Daemon` を選びます。
更新操作はすべて `Updates` サブメニュー内です。
安全な更新適用は未実装のため、ダウンロードとインストールは無効です。

## 文書

- [設定](CONFIG.ja.md)
- [コマンド](COMMANDS.ja.md)
- [MCP接続](MCP_SETUP.ja.md)
- [依存関係](PACKAGES.md)（英語）
- [安全性](SECURITY.md)（英語）

Windows Serviceや管理者権限を必要とする処理はありません。
Claude CodeとCodexは既に起動しているHTTP Daemonへ接続するクライアントとして利用します。
configure／unconfigureは他の設定を保持し、環境変数名を参照するHTTP接続項目だけを登録します。
auth-shellは手動起動したPowerShellへ認証情報を渡し、平文トークンを保存しません。詳細はMCP接続文書を参照してください。
ユーザー設定への登録は済んでいますが、対話セッションからのツール呼び出しは未確認です。Daemonを自動起動する設定を登録しないでください。
