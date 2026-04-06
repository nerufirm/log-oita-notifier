# LOG OITA 新着記事通知 セットアップガイド

## 概要

[LOG OITA](https://log-oita.com/) の新着記事を自動監視し、Gemini API（gemini-2.0-flash）で20文字以内に要約して Google Chat に通知するシステムです。

通知メッセージでは記事タイトルを鉤括弧（「」）付きで表示し、要約とリンクを添えて送信します。

## 通知フォーマット例

```
📰 LOG OITA 新着記事

「ゆめタウン別府の『食事処 春日』が閉店していました」

ゆめタウン別府の春日が閉店

🔗 https://log-oita.com/...
```

## 必要な準備

### 1. Google Chat Webhook URL の取得

1. Google Chat でメッセージを送信したいスペースを開く
2. スペース名をクリック → 「アプリと統合」を選択
3. 「Webhook を追加」をクリック
4. 名前を入力する（例: LOG OITA 通知）
5. 表示された URL をコピーして控えておく

### 2. Gemini API キーの取得

1. [Google AI Studio](https://aistudio.google.com/apikey) にアクセス
2. 「API キーを作成」をクリック
3. 生成されたキーをコピーして控えておく

### 3. GitHub Secrets の設定

GitHub Actions で自動実行するために、リポジトリにシークレットを登録します。

1. GitHub リポジトリのページを開く
2. **Settings** → **Secrets and variables** → **Actions** に移動
3. 「New repository secret」をクリックし、以下の2つを追加する

| Name | 値 |
|---|---|
| `GOOGLE_CHAT_WEBHOOK_URL` | 手順1で取得した Webhook URL |
| `GEMINI_API_KEY` | 手順2で取得した Gemini API キー |

## ローカルでのテスト方法

```bash
# 1. リポジトリをクローン
git clone <リポジトリURL>
cd log-oita-notifier

# 2. .env ファイルを作成
cp .env.example .env

# 3. .env を編集し、API キーと Webhook URL を記入
#    GOOGLE_CHAT_WEBHOOK_URL=https://chat.googleapis.com/...
#    GEMINI_API_KEY=AIza...

# 4. 依存パッケージをインストール
pip install -r requirements.txt

# 5. 実行
python notifier.py
```

## 仕組み

- **GitHub Actions** が 10 分ごとにワークフロー（`.github/workflows/notify.yml`）を実行する
- `notifier.py` が LOG OITA の RSS フィード（`https://log-oita.com/feed/`）を取得する
- 新着記事を検出すると、Gemini API で本文を 20 文字以内に要約する
- 要約結果とタイトル・リンクを Google Chat の Webhook に送信する
- 通知済みの記事 URL は `last_seen.json` に記録し、重複通知を防止する
- `last_seen.json` は GitHub Actions が自動でコミット・プッシュして永続化する

## ファイル構成

```
log-oita-notifier/
├── .env.example                  # 環境変数のテンプレート
├── .github/
│   └── workflows/
│       └── notify.yml            # GitHub Actions ワークフロー（10分間隔）
├── last_seen.json                # 通知済み記事の記録（自動生成）
├── notifier.py                   # メインスクリプト
├── requirements.txt              # Python 依存パッケージ
└── SETUP.md                      # このファイル
```

## 依存パッケージ

| パッケージ | 用途 |
|---|---|
| `feedparser` | RSS フィードの解析 |
| `requests` | HTTP リクエスト（RSS 取得・Webhook 送信） |
| `beautifulsoup4` | HTML からテキストを抽出 |
| `google-genai` | Gemini API による要約生成 |

## トラブルシューティング

- **「環境変数 GOOGLE_CHAT_WEBHOOK_URL が未設定です」と表示される**: `.env` ファイルに `GOOGLE_CHAT_WEBHOOK_URL` が正しく設定されているか確認する
- **「環境変数 GEMINI_API_KEY が未設定です」と表示される**: `.env` ファイルに `GEMINI_API_KEY` が正しく設定されているか確認する
- **Gemini API のレート制限エラー（429）**: 自動で最大3回リトライする（40秒間隔）。頻発する場合は API の利用上限を確認する
- **GitHub Actions が動かない**: リポジトリの Settings → Secrets で `GOOGLE_CHAT_WEBHOOK_URL` と `GEMINI_API_KEY` が登録されているか確認する
