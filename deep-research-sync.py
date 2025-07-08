import os, time
from typing import Optional
from datetime import datetime
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import DeepResearchTool, MessageRole, ThreadMessage
from dotenv import load_dotenv

load_dotenv()

def log_with_timestamp(message: str) -> None:
    """タイムスタンプ付きでログを出力"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def fetch_and_print_new_agent_response(
    thread_id: str,
    agents_client: AgentsClient,
    last_message_id: Optional[str] = None,
) -> Optional[str]:
    response = agents_client.messages.get_last_message_by_role(
        thread_id=thread_id,
        role=MessageRole.AGENT,
    )
    if not response or response.id == last_message_id:
        return last_message_id  # No new content

    log_with_timestamp("新しいエージェント応答を受信")
    print("\nAgent response:")
    print("\n".join(t.text.value for t in response.text_messages))

    for ann in response.url_citation_annotations:
        print(f"URL Citation: [{ann.url_citation.title}]({ann.url_citation.url})")

    return response.id


def create_research_summary(
        message : ThreadMessage,
        filepath: str = "research_summary.md"
) -> None:
    if not message:
        print("No message content provided, cannot create research summary.")
        return

    with open(filepath, "w", encoding="utf-8") as fp:
        # Write text summary
        text_summary = "\n\n".join([t.text.value.strip() for t in message.text_messages])
        fp.write(text_summary)

        # Write unique URL citations, if present
        if message.url_citation_annotations:
            fp.write("\n\n## References\n")
            seen_urls = set()
            for ann in message.url_citation_annotations:
                url = ann.url_citation.url
                title = ann.url_citation.title or url
                if url not in seen_urls:
                    fp.write(f"- [{title}]({url})\n")
                    seen_urls.add(url)

    print(f"Research summary written to '{filepath}'.")


project_client = AIProjectClient(
    endpoint=os.environ["PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential(),
)

# Bing接続IDを.envファイルから取得、または自動構築を試行
if "BING_CONNECTION_ID" in os.environ and os.environ["BING_CONNECTION_ID"].strip():
    conn_id = os.environ["BING_CONNECTION_ID"]
    log_with_timestamp(f"環境変数から接続IDを取得: {conn_id}")
else:
    log_with_timestamp("BING_CONNECTION_IDが設定されていません。接続IDの自動構築を試行します...")
    
    # プロジェクトエンドポイントから接続IDを推定
    project_endpoint = os.environ["PROJECT_ENDPOINT"]
    # エンドポイント例: https://makuroda-deep-research-resource.services.ai.azure.com/api/projects/makuroda-deep-research
    
    try:
        # プロジェクトのメタデータから接続リストを取得を試行
        connections = project_client.connections.list()
        
        # bingforo3deepresearch接続を検索
        bing_connection = None
        for connection in connections:
            if connection.name == os.environ["BING_RESOURCE_NAME"]:
                bing_connection = connection
                break
        
        if bing_connection:
            conn_id = bing_connection.id
            log_with_timestamp(f"Bing接続を自動取得: {conn_id}")
        else:
            log_with_timestamp(f"Bing接続 '{os.environ['BING_RESOURCE_NAME']}' が見つかりません")
            exit(1)
            
    except Exception as e:
        log_with_timestamp(f"接続の自動取得に失敗: {e}")
        log_with_timestamp("Azure AI Foundryポータルから手動で接続IDを取得して.envファイルに設定してください")
        log_with_timestamp("Management Center -> Connected resources -> bingforo3deepresearch -> 完全なリソースIDをコピー")
        exit(1)


# Initialize a Deep Research tool with Bing Connection ID and Deep Research model deployment name
deep_research_tool = DeepResearchTool(
    bing_grounding_connection_id=conn_id,
    deep_research_model=os.environ["DEEP_RESEARCH_MODEL_DEPLOYMENT_NAME"],
)

# Create Agent with the Deep Research tool and process Agent run
with project_client:

    with project_client.agents as agents_client:

        # Create a new agent that has the Deep Research tool attached.
        # NOTE: To add Deep Research to an existing agent, fetch it with `get_agent(agent_id)` and then,
        # update the agent with the Deep Research tool.
        agent = agents_client.create_agent(
            model=os.environ["MODEL_DEPLOYMENT_NAME"],
            name="my-agent",
            instructions="You are a helpful Agent that assists in researching scientific topics.",
            tools=deep_research_tool.definitions,
        )

        # [END create_agent_with_deep_research_tool]
        log_with_timestamp(f"エージェントを作成しました - ID: {agent.id}")

        # Create thread for communication
        thread = agents_client.threads.create()
        log_with_timestamp(f"スレッドを作成しました - ID: {thread.id}")

        # Create message to thread
        message = agents_client.messages.create(
            thread_id=thread.id,
            role="user",
            content=(
                """
                マイクロソフトの2025年の最新動向について調査してください。
                1. **技術革新や製品発表**（例：AI、クラウド、Windowsなど）  
                2. **ビジネス戦略**（例：政府との提携、買収、パートナーシップなど）  
                3. **財務状況**（例：収益、株価、利益率など）  
                4. **社会的責任や環境施策**（例：持続可能性プロジェクトなど）  
                5. **その他特定分野のトピック**（例：ゲーム事業、Azure、GitHub、LinkedInなど）
                """
            ),
        )
        log_with_timestamp(f"メッセージを作成しました - ID: {message.id}")

        log_with_timestamp("処理を開始します（数分かかる場合があります）...")
        # Poll the run as long as run status is queued or in progress
        run = agents_client.runs.create(thread_id=thread.id, agent_id=agent.id)
        last_message_id = None
        status_count = 0
        
        while run.status in ("queued", "in_progress"):
            time.sleep(1)
            run = agents_client.runs.get(thread_id=thread.id, run_id=run.id)
            status_count += 1

            last_message_id = fetch_and_print_new_agent_response(
                thread_id=thread.id,
                agents_client=agents_client,
                last_message_id=last_message_id,
            )
            
            # 10秒ごとに進行状況を表示
            if status_count % 10 == 0:
                log_with_timestamp(f"実行中... ステータス: {run.status} ({status_count}秒経過)")
            else:
                print(f"Run status: {run.status}")

        log_with_timestamp(f"実行完了 - ステータス: {run.status}, ID: {run.id}")

        if run.status == "failed":
            log_with_timestamp(f"実行失敗: {run.last_error}")

        # Fetch the final message from the agent in the thread and create a research summary
        log_with_timestamp("最終メッセージを取得中...")
        final_message = agents_client.messages.get_last_message_by_role(
            thread_id=thread.id, role=MessageRole.AGENT
        )
        if final_message:
            log_with_timestamp("研究サマリーを作成中...")
            create_research_summary(final_message)

        # Clean-up and delete the agent once the run is finished.
        # NOTE: Comment out this line if you plan to reuse the agent later.
        agents_client.delete_agent(agent.id)
        log_with_timestamp("エージェントを削除しました")