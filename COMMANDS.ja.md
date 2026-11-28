# コマンド

[English](COMMANDS.md) | 日本語

WindowsのPowerShellで、リポジトリ内から `uv sync --locked` を実行した後に使用します。
ソースから実行する場合、各コマンドの先頭へ `uv run` を付けます。
`--data-root <パス>` はサブコマンドより前へ指定します。

| コマンド | 動作 |
| --- | --- |
| `spriteforge start` | 通常ユーザーの独立プロセスを起動、または認証済みの既存Daemonを報告 |
| `spriteforge stop` | 認証付きの正常停止を要求。PIDによる強制終了は実施しない |
| `spriteforge restart` | 停止と多重起動防止の解放を待ち、再起動 |
| `spriteforge status` | 停止・稼働・エラーと、検証した実行情報を返す |
| `spriteforge serve` | 開発用にHTTPを前面実行 |
| `spriteforge stdio` | 明示的な独立STDIO MCP。HTTP Daemonは操作しない |
| `spriteforge logs [--lines 50] [--follow]` | Daemonの直近ログを表示、または追記を監視 |
| `spriteforge doctor` | 設定・保存先・トークン・ポートを診断。DBとProviderは未実装と表示 |
| `spriteforge tray` | Windows通知領域のアプリを起動 |
| `spriteforge update check` | 公式リリースを取得。既定は安定版のみ |
| `spriteforge update status` | 更新が未準備であることを表示 |
| `spriteforge update configure` | 設定ファイルの場所とプレリリース設定を表示 |
| `spriteforge update download` | 検証済みの保存処理が未実装として失敗 |
| `spriteforge update apply` | 安全なインストール・復旧が未実装として失敗 |
| `spriteforge --version` | 初期開発版 `0.0.0.0` を表示 |
| `spriteforge configure codex\|claude [--dry-run] [--config-path <ファイル>]` | 他の設定を保持してHTTP接続項目を登録 |
| `spriteforge unconfigure codex\|claude [--dry-run] [--config-path <ファイル>]` | この環境で登録した、変更されていない項目だけを解除 |
| `spriteforge auth-shell` | DPAPIトークンをそのプロセスの環境変数にだけ渡したPowerShellを明示起動 |

通常の結果は標準出力へJSONで返します。エラーは安全なJSONで標準エラー出力へ返し、終了コード1にします。
Ctrl+Cは130、引数の誤りは2です。STDIOの標準出力はMCP通信専用です。
`logs` はテキスト、`--version` はバージョン文字列を表示します。

稼働状況にはPID、接続先、起動ごとの識別子、稼働時間、ジョブ件数を含みます。
ジョブ件数は現時点では0で、`jobs_available: false` によりジョブ管理が未実装であることを示します。
起動済みなら再度の `start` は同じPIDと `already_running: true` を返します。
Daemon不在は `stopped`、ポートの占有や認証・識別の失敗は `error` です。無関係なプロセスは終了しません。

トレイの更新操作は `Updates` にまとめています。ソースアーカイブと対応パッケージのないリリースは
ダウンロード・インストールできません。

登録にはクライアントの実行ファイルがPATH上に必要です。解除はクライアント削除後も実行できます。
`--dry-run` は書き込みません。競合、不正形式、登録後に変更された設定は上書きせず失敗します。
設定は原子的に保存し、管理情報の保存に失敗したら元の設定へ戻します。
認証用PowerShellには既存トークンが必要で、Daemonは起動しません。
ユーザー環境変数として永続化せず、PowerShell終了時にその環境を破棄します。
実際のクライアント設定変更は、これらのコマンドの実装とは別の明示的な操作です。
