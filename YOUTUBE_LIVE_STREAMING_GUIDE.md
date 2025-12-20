# YouTube Live Streaming Guide

このガイドでは、災害情報ダッシュボードをYouTube Liveで配信する方法を説明します。

## 📋 目次

1. [概要](#概要)
2. [必要な環境](#必要な環境)
3. [依存関係のインストール](#依存関係のインストール)
4. [YouTube Studioの設定](#youtube-studioの設定)
5. [配信の開始方法](#配信の開始方法)
6. [トラブルシューティング](#トラブルシューティング)

## 概要

このシステムは、災害情報ダッシュボードをリアルタイムでYouTube Liveに配信する機能を提供します。

### 主な機能

- ✅ FFmpegを使用した高品質ストリーミング
- ✅ ブラウザベースのキャプチャ
- ✅ 1920x1080 Full HD 解像度
- ✅ 30fps フレームレート
- ✅ 4.5Mbps ビットレート
- ✅ リアルタイム配信ステータス監視

## 必要な環境

### システム要件

- Ubuntu 20.04 LTS 以上
- 最小 4GB RAM (推奨 8GB以上)
- 安定したインターネット接続 (アップロード速度 6Mbps 以上推奨)
- FFmpeg 4.0 以上
- Xvfb (X Virtual Framebuffer)
- Chromium Browser

### 必要な権限

- YouTube チャンネルの管理権限
- ライブ配信機能の有効化 (YouTubeで有効化に24時間かかる場合があります)

## 依存関係のインストール

### 自動インストール（推奨）

```bash
cd /home/ubuntu/Disaster-info-System/backend
./install_streaming_dependencies.sh
```

### 手動インストール

```bash
# パッケージリストを更新
sudo apt-get update

# FFmpegをインストール
sudo apt-get install -y ffmpeg

# Xvfbをインストール
sudo apt-get install -y xvfb x11-xserver-utils xfonts-base xfonts-75dpi xfonts-100dpi

# インストールを確認
ffmpeg -version
Xvfb -help
```

## YouTube Studioの設定

### 1. YouTube Studioにアクセス

1. [YouTube Studio](https://studio.youtube.com) を開く
2. 右上のアイコンからチャンネルを選択

### 2. ライブ配信を有効化

1. 左メニューから「ライブ配信」を選択
2. 初回の場合、ライブ配信機能の有効化が必要（最大24時間かかります）

### 3. ストリームキーを取得

1. 「ライブ配信」→「ストリーム」を選択
2. 「ストリームキー」セクションを探す
3. 「コピー」ボタンでストリームキーをコピー

例:
```
ストリームキー: 4dzh-z5y1-69km-gw0u-0342
ストリームURL: rtmp://a.rtmp.youtube.com/live2
```

## 配信の開始方法

### Web UIから配信

1. ダッシュボードにアクセス: `http://49.212.176.130/`

2. 「YouTube Live」タブを選択

3. 「配信設定」タブで以下を入力:
   - **ストリームキー**: YouTube Studioで取得したキー
   - **ストリームURL**: `rtmp://a.rtmp.youtube.com/live2`（通常は変更不要）
   - **ダッシュボードURL**: `http://49.212.176.130/`（通常は変更不要）

4. 「設定を保存」をクリック

5. 「配信を開始」ボタンをクリック

6. 配信が開始されるまで10〜30秒待つ

7. YouTube Studioで配信が開始されたことを確認

### APIから配信

```bash
# 配信開始
curl -X POST "http://49.212.176.130/api/streaming/start?stream_key=YOUR_STREAM_KEY"

# 配信停止
curl -X POST "http://49.212.176.130/api/streaming/stop"

# ステータス確認
curl -X GET "http://49.212.176.130/api/streaming/status"
```

### コマンドラインから配信

```bash
cd /home/ubuntu/Disaster-info-System/backend

# Python スクリプトを直接実行
python3 youtube_live_streaming.py
```

## トラブルシューティング

### エラー: "Missing required dependencies"

**原因**: FFmpegまたはXvfbがインストールされていません。

**解決方法**:
```bash
cd /home/ubuntu/Disaster-info-System/backend
./install_streaming_dependencies.sh
```

### エラー: "Failed to start streaming"

**原因**: 
- ストリームキーが無効
- インターネット接続の問題
- YouTube側の制限

**解決方法**:
1. ストリームキーを再確認
2. インターネット接続を確認
3. YouTube Studioで配信ステータスを確認
4. バックエンドログを確認: `pm2 logs main`

### 配信が開始されない

**チェックリスト**:
- [ ] FFmpegがインストールされているか確認: `which ffmpeg`
- [ ] Xvfbがインストールされているか確認: `which Xvfb`
- [ ] バックエンドが起動しているか確認: `pm2 status`
- [ ] ストリームキーが正しいか確認
- [ ] ファイアウォールでRTMPポート(1935)が開いているか確認

### 配信が遅延する

**原因**: 
- サーバーのリソース不足
- ネットワーク帯域の問題

**解決方法**:
1. ビットレートを下げる（コードで調整が必要）
2. 解像度を下げる（コードで調整が必要）
3. サーバーのリソースを確認: `htop`

### 配信が途切れる

**原因**:
- ネットワークの不安定
- サーバーのリソース不足

**解決方法**:
1. ネットワーク接続を確認
2. サーバーの CPU/メモリ使用率を確認
3. 配信を再起動

## 技術仕様

### ストリーミング設定

```
解像度: 1920x1080 (Full HD)
フレームレート: 30 fps
ビデオビットレート: 4500 kbps
オーディオビットレート: 128 kbps
オーディオサンプルレート: 44100 Hz
エンコーダー: libx264
プリセット: veryfast
ピクセルフォーマット: yuv420p
GOPサイズ: 60 (2秒)
```

### API エンドポイント

#### POST /api/streaming/start
配信を開始

**パラメータ**:
- `stream_key` (required): YouTube ストリームキー

**レスポンス**:
```json
{
  "status": "started",
  "message": "YouTube Live streaming started successfully",
  "stream_info": {
    "is_streaming": true,
    "dashboard_url": "http://49.212.176.130/",
    "stream_url": "rtmp://a.rtmp.youtube.com/live2",
    "resolution": "1920x1080",
    "framerate": 30,
    "video_bitrate": "4500k"
  }
}
```

#### POST /api/streaming/stop
配信を停止

**レスポンス**:
```json
{
  "status": "stopped",
  "message": "YouTube Live streaming stopped successfully"
}
```

#### GET /api/streaming/status
配信ステータスを取得

**レスポンス**:
```json
{
  "is_streaming": true,
  "dashboard_url": "http://49.212.176.130/",
  "stream_url": "rtmp://a.rtmp.youtube.com/live2",
  "resolution": "1920x1080",
  "framerate": 30,
  "video_bitrate": "4500k",
  "process_alive": true
}
```

## サポート

問題が解決しない場合は、以下の情報を含めてご連絡ください:

1. エラーメッセージ
2. バックエンドログ: `pm2 logs main`
3. システム情報: `uname -a`
4. 依存関係のバージョン:
   ```bash
   ffmpeg -version
   Xvfb -help | head -n1
   chromium-browser --version
   ```

## 参考資料

- [YouTube Live Streaming API](https://developers.google.com/youtube/v3/live/getting-started)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [RTMP Specification](https://www.adobe.com/devnet/rtmp.html)

