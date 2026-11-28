# 設定

[English](CONFIG.md) | 日本語

## 保存先と優先順位

既定のデータ保存先は `%LOCALAPPDATA%\SpriteForgeMCP` です。
開発用には `spriteforge --data-root <絶対ディレクトリ> <コマンド>` で保存先を変更できます。
設定は `<データ保存先>\config\settings.toml` から読み込み、各コマンドの実行前に検証します。
ファイルがなければ既定値を使います。不明な項目や不正値は終了コード1になります。
設定の変更はDaemonの再起動後に反映されます。

## 設定項目

```toml
port = 8765
startup_timeout = 60
shutdown_timeout = 20
max_request_bytes = 1048576
tray_poll_seconds = 3
update_prereleases = false
```

| 項目 | 既定値 | 許容値 |
| --- | --- | --- |
| `port` | 8765 | 1024～65535 |
| `startup_timeout` | 60 | 1～120秒 |
| `shutdown_timeout` | 20 | 1～120秒 |
| `max_request_bytes` | 1048576 | 1024～16777216バイト |
| `tray_poll_seconds` | 3 | 2～5秒 |
| `update_prereleases` | false | 真偽値 |

待受アドレスは常に `127.0.0.1` で、外部公開へ変更できません。
更新元のリポジトリは `katsushoe/SpriteForge` に固定しています。

## 保存内容

`runtime` に診断用メタデータとローテーションするログを保存します。
`secrets/local-token.dpapi` に現在のWindowsユーザーのDPAPIで暗号化した認証トークンを保存します。
トークンをプロセスのコマンドラインへ渡すことはありません。
`db`、`projects`、`cache`、`output` は後続の画像・ジョブ機能用です。
PIDメタデータだけを根拠にプロセスを終了することはありません。

セッションの多重起動防止はデータ保存先を変更しても共通です。
別の保存先を使う前に、元の保存先を指定して既存Daemonを停止してください。
環境変数 `SPRITEFORGE_TEST_MUTEX_NAMESPACE` はテスト専用です。テストが稼働中の利用者Daemonと衝突しないよう使用します。通常利用では設定しないでください。
