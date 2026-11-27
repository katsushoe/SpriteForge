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
configure／unconfigure、認証情報の安全なクライアント設定、実クライアントの接続確認は未完了です。
URLだけを登録して認証トークンを渡さない場合はHTTP 401になります。
暗号化したトークンファイルをクライアント設定へコピーしたり、トークンを公開したりしないでください。

SDK統合テストでは2クライアントの同時接続、初期化、ツール一覧、構造化したバージョンの出力、
不明ツールのエラーを検証します。実際のAIアプリ内での検証済みという意味ではありません。

## 問題が起きた場合

WindowsのPowerShellでリポジトリを開き、`uv run spriteforge status`、
`uv run spriteforge doctor`、`uv run spriteforge logs` を使用します。
`running` では検証済みDaemonのPIDと接続先を表示します。`stopped` なら明示的に起動します。
`error` ならログと設定を確認します。CLIはポートを占有するプロセスを強制終了しません。

プロトコルの診断時だけ `uv run spriteforge stdio` を手動実行できます。
この操作はHTTPを起動・停止しません。標準出力はMCP通信専用で、ログは標準エラー出力とファイルです。
