# pylint: disable=line-too-long,useless-suppression
# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------

"""
DESCRIPTION:
    This sample demonstrates how to use Agent operations with the Deep Research tool from
    the Azure Agents service through the **asynchronous** Python client. Deep Research issues
    external Bing Search queries and invokes an LLM, so each run can take several minutes
    to complete.

    For more information see the Deep Research Tool document: https://aka.ms/agents-deep-research

USAGE:
    python sample_agents_deep_research_async.py

    Before running the sample:

    pip install azure-ai-projects azure-ai-agents azure-identity aiohttp

    Set these environment variables with your own values:
    1) PROJECT_ENDPOINT - The Azure AI Project endpoint, as found in the Overview
                          page of your Azure AI Foundry portal.
    2) MODEL_DEPLOYMENT_NAME - The deployment name of the arbitration AI model, as found under the "Name" column in
       the "Models + endpoints" tab in your Azure AI Foundry project.
    3) DEEP_RESEARCH_MODEL_DEPLOYMENT_NAME - The deployment name of the Deep Research AI model, as found under the "Name" column in
       the "Models + endpoints" tab in your Azure AI Foundry project.
    4) AZURE_BING_CONNECTION_ID - The ID of the Bing connection, in the format of:
       /subscriptions/{subscription-id}/resourceGroups/{resource-group-name}/providers/Microsoft.MachineLearningServices/workspaces/{workspace-name}/connections/{connection-name}
"""

import asyncio
import os
from typing import Optional
from datetime import datetime

from azure.ai.projects.aio import AIProjectClient
from azure.ai.agents.aio import AgentsClient
from azure.ai.agents.models import DeepResearchTool, MessageRole, ThreadMessage
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

def log_with_timestamp(message: str) -> None:
    """タイムスタンプ付きでログを出力"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


async def fetch_and_print_new_agent_response(
    thread_id: str,
    agents_client: AgentsClient,
    last_message_id: Optional[str] = None,
) -> Optional[str]:
    response = await agents_client.messages.get_last_message_by_role(
        thread_id=thread_id,
        role=MessageRole.AGENT,
    )

    if not response or response.id == last_message_id:
        return last_message_id

    log_with_timestamp("新しいエージェント応答を受信")
    print("\nAgent response:")
    print("\n".join(t.text.value for t in response.text_messages))

    # Print citation annotations (if any)
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


async def main() -> None:
    log_with_timestamp("Deep Research (非同期版) を開始します")

    project_client = AIProjectClient(
        endpoint=os.environ["PROJECT_ENDPOINT"],
        credential=DefaultAzureCredential(),
    )
    log_with_timestamp("Azure AI Project Clientを初期化しました")

    # Initialize a Deep Research tool with Bing Connection ID and Deep Research model deployment name
    log_with_timestamp("Deep Research Toolを初期化中...")
    deep_research_tool = DeepResearchTool(
        bing_grounding_connection_id=os.environ["AZURE_BING_CONNECTION_ID"],
        deep_research_model=os.environ["DEEP_RESEARCH_MODEL_DEPLOYMENT_NAME"],
    )
    log_with_timestamp(f"Deep Research Tool初期化完了 - モデル: {os.environ['DEEP_RESEARCH_MODEL_DEPLOYMENT_NAME']}")

    async with project_client:

        agents_client = project_client.agents

        # Create a new agent that has the Deep Research tool attached.
        # NOTE: To add Deep Research to an existing agent, fetch it with `get_agent(agent_id)` and then,
        # update the agent with the Deep Research tool.
        agent = await agents_client.create_agent(
            model=os.environ["MODEL_DEPLOYMENT_NAME"],
            name="my-agent",
            instructions="You are a helpful Agent that assists in researching scientific topics.",
            tools=deep_research_tool.definitions,
        )
        log_with_timestamp(f"エージェントを作成しました - ID: {agent.id}")

        # Create thread for communication
        thread = await agents_client.threads.create()
        log_with_timestamp(f"スレッドを作成しました - ID: {thread.id}")

        # Create message to thread
        message = await agents_client.messages.create(
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
        run = await agents_client.runs.create(thread_id=thread.id, agent_id=agent.id)
        last_message_id: Optional[str] = None
        status_count = 0
        
        while run.status in ("queued", "in_progress"):
            await asyncio.sleep(1)
            run = await agents_client.runs.get(thread_id=thread.id, run_id=run.id)
            status_count += 1

            last_message_id = await fetch_and_print_new_agent_response(
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
        final_message = await agents_client.messages.get_last_message_by_role(
            thread_id=thread.id, role=MessageRole.AGENT
        )
        if final_message:
            log_with_timestamp("研究サマリーを作成中...")
            create_research_summary(final_message)

        # Clean-up and delete the agent once the run is finished.
        # NOTE: Comment out this line if you plan to reuse the agent later.
        await agents_client.delete_agent(agent.id)
        log_with_timestamp("エージェントを削除しました")


if __name__ == "__main__":
    asyncio.run(main())