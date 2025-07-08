# Deep Research Project

このプロジェクトは、Azure AI Foundry Agents Service を使用してDeep Research機能を実装したPythonアプリケーションです。

## 概要

Azure AI Foundry Agents Serviceの Deep Research Tool を使用して、指定したトピックについて包括的な調査を行い、結果をMarkdown形式で保存します。同期版と非同期版の両方を提供しています。

## ファイル構成

- `deep-research-sync.py` - 同期版のDeep Research実装
- `deep-research-async.py` - 非同期版のDeep Research実装
- `research_summary-sync.md` - 同期版の調査結果
- `research_summary-async.md` - 非同期版の調査結果
- `.env-sample` - 環境変数設定のサンプル
- `requirements.txt` - 必要なPythonパッケージ一覧

## セットアップ

### 前提条件

- Python 3.8以上
- Azure AI Foundry Projectsリソース
- Bing Search リソース (Deep Research用)

### インストール

1. リポジトリをクローンします：
```bash
git clone https://github.com/MamoruKuroda/DeepResearch.git
cd DeepResearch
```

2. 仮想環境を作成・有効化します：
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# または
source venv/bin/activate  # macOS/Linux
```

3. 依存関係をインストールします：
```bash
pip install -r requirements.txt
```

4. 環境変数を設定します：
```bash
cp .env-sample .env
# .envファイルを編集して必要な値を設定
```

### 環境変数の設定

`.env`ファイルに以下の値を設定してください：

```
PROJECT_ENDPOINT=https://your-project.services.ai.azure.com/api/projects/your-project
BING_CONNECTION_ID=your-bing-connection-id
BING_RESOURCE_NAME=your-bing-resource-name
DEEP_RESEARCH_MODEL_DEPLOYMENT_NAME=your-deep-research-model
MODEL_DEPLOYMENT_NAME=your-model-deployment
```

## 使用方法

### 同期版の実行

```bash
python deep-research-sync.py
```

### 非同期版の実行

```bash
python deep-research-async.py
```

実行後、調査結果が`research_summary-sync.md`または`research_summary-async.md`に保存されます。

## 機能

- **Deep Research**: Bing Searchを使用した包括的な調査
- **URL Citations**: 参考文献の自動収集
- **Markdown出力**: 調査結果の構造化された出力
- **同期・非同期対応**: 用途に応じた実行方式の選択

## 参考サイト

このプロジェクトは以下のサイトを参考にして作成されています：

- [Zenn - Azure AI Agentsを使ったDeep Research](https://zenn.dev/microsoft/articles/19529991cd0653)
- [Azure SDK for Python - Deep Research Sample](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/ai/azure-ai-agents/samples/agents_async/sample_agents_deep_research_async.py)

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 作成者

[Mamoru Kuroda](https://github.com/MamoruKuroda)
