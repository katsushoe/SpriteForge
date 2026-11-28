# MCP接続

[English](MCP_SETUP.md) | 日本語

## 実行方式

ユーザーがCLIまたはトレイでDaemonを起動します。Claude CodeとCodexはStreamable HTTPで
`http://127.0.0.1:8765/mcp` に接続するだけです。通常利用でコマンドやSTDIOの子プロセスを
登録しないでください。AIクライアントを終了してもDaemonは停止しません。

HTTP認証にはWindows DPAPIで保護したローカルトークンを使います。
`/health` は認証不要、`/status`、`/mcp`、`/control/stop` は認証必須です。
MCPには起動・停止のツールを公開しません。HTTP／STDIOで共通の初期ツールは
読み取り専用の `get_version` のみです。

## クライアント対応状況

今回の実装で実際のClaude Code・Codex設定は変更していません。
configure／unconfigureは、他の項目を保持するユーザー単位のHTTP登録・解除に対応しました。
Codexの既定は `$CODEX_HOME/config.toml` または `~/.codex/config.toml`、Claudeは
`~/.claude.json`（`CLAUDE_CONFIG_DIR` 指定時はその中の `.claude.json`）です。
`--config-path` で明示的に変更できます。実クライアントの接続確認は未完了です。
URLだけを登録して認証トークンを渡さない場合はHTTP 401になります。
暗号化したトークンファイルをクライアント設定へコピーしたり、トークンを公開したりしないでください。

登録項目は `SPRITEFORGE_MCP_TOKEN` を参照します。Codexは `bearer_token_env_var`、Claudeは
HTTPヘッダーの `Bearer ${SPRITEFORGE_MCP_TOKEN}` を使い、実トークンをファイルへ書きません。
TOMLのコメントと他の接続項目を保持し、所有元不明または変更済みの競合項目は上書きしません。
所有情報は `<データ保存先>/config/client-registrations.json` に保存します。
登録と解除では同じデータ保存先を使います。対応する所有情報がなければ項目を削除しません。

開発用CLI接続では `spriteforge auth-shell` がDPAPIから復号したトークンを引き継ぐ前面のPowerShellを開きます。
そのPowerShellでクライアントを手動起動します。Daemonは先に起動する必要があり、クライアントは起動しません。
トークンをWindowsのユーザー環境変数へ保存せず、プロセス引数にも含めません。
PowerShellを閉じると、この認証用環境も終了します。起動済みのデスクトップクライアントには、
後から開いたPowerShellの環境変数は引き継がれません。デスクトップへの認証設定と対話接続は未確認です。

形式の根拠：[Codex MCP設定](https://learn.chatgpt.com/docs/extend/mcp) と
[Claude Code MCP設定](https://code.claude.com/docs/en/mcp)（英語）。

SDK統合テストでは2クライアントの同時接続、初期化、ツール一覧、構造化したバージョンの出力、
不明ツールのエラーを検証します。実際のAIアプリ内での検証済みという意味ではありません。

## 問題が起きた場合

WindowsのPowerShellでリポジトリを開き、`uv run spriteforge status`、
`uv run spriteforge doctor`、`uv run spriteforge logs` を使用します。
`running` では検証済みDaemonのPIDと接続先を表示します。`stopped` なら明示的に起動します。
`error` ならログと設定を確認します。CLIはポートを占有するプロセスを強制終了しません。

プロトコルの診断時だけ `uv run spriteforge stdio` を手動実行できます。
この操作はHTTPを起動・停止しません。標準出力はMCP通信専用で、ログは標準エラー出力とファイルです。
