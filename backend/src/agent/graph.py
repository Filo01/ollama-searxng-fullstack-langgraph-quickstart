import os
import requests
from agent.tools_and_schemas import SearchQueryList, Reflection
from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langgraph.types import Send
from langgraph.graph import StateGraph
from langgraph.graph import START, END
from langchain_core.runnables import RunnableConfig
from ollama import chat as ollama_chat

from agent.state import (
    OverallState,
    QueryGenerationState,
    ReflectionState,
    WebSearchState,
)
from agent.configuration import Configuration
from agent.prompts import (
    get_current_date,
    query_writer_instructions,
    web_searcher_instructions,
    reflection_instructions,
    answer_instructions,
)
from agent.utils import (
    get_citations,
    get_research_topic,
    insert_citation_markers,
    resolve_urls,
)

load_dotenv()

# Nodes

def generate_query(state: OverallState, config: RunnableConfig) -> QueryGenerationState:
    """LangGraph node that generates search queries based on the User's question using Ollama."""
    configurable = Configuration.from_runnable_config(config)
    if state.get("initial_search_query_count") is None:
        state["initial_search_query_count"] = configurable.number_of_initial_queries

    current_date = get_current_date()
    formatted_prompt = query_writer_instructions.format(
        current_date=current_date,
        research_topic=get_research_topic(state["messages"]),
        number_queries=state["initial_search_query_count"],
    )
    # Use Ollama to generate queries
    response = ollama_chat(
        model=configurable.query_generator_model,
        messages=[{"role": "user", "content": formatted_prompt}],
    )
    import json
    import re
    content = response["message"]["content"]
    print("Ollama response:", content)  # Debug print
    try:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            result = json.loads(match.group(0))
        else:
            print("No JSON object found in Ollama response.")
            result = {"query": [], "rationale": "No JSON object found in Ollama response. See logs for details."}
    except Exception as e:
        print(f"Error parsing Ollama response as JSON: {e}\nResponse was: {content}")
        result = {"query": [], "rationale": f"Error parsing Ollama response as JSON: {e}. See logs for details."}
    return {"query_list": result.get("query", [])}


def continue_to_web_research(state: QueryGenerationState):
    return [
        Send("web_research", {"search_query": search_query, "id": int(idx)})
        for idx, search_query in enumerate(state["query_list"])
    ]


def web_research(state: WebSearchState, config: RunnableConfig) -> OverallState:
    """LangGraph node that performs web research using SearxNG and synthesizes with Ollama."""
    configurable = Configuration.from_runnable_config(config)
    searxng_url = getattr(configurable, "searxng_url", os.getenv("SEARXNG_URL", "http://localhost:8080/search"))
    query = state["search_query"]
    params = {
        "q": query,
        "format": "json",
        "engines": "google,duckduckgo,bing",
        "language": "en",
        "safesearch": 0,
        "categories": "general",
    }
    try:
        resp = requests.get(searxng_url, params=params, timeout=10)
        results = resp.json().get("results", [])
    except Exception:
        results = []
    # Compose a summary of the top results
    snippets = []
    sources = []
    for idx, r in enumerate(results[:5]):
        snippet = r.get("content") or r.get("title") or ""
        url = r.get("url")
        if snippet and url:
            snippets.append(f"[{snippet}]({url})")
            sources.append({"label": f"Source {idx+1}", "short_url": url, "value": url})
    summary = "\n".join(snippets)
    # Use Ollama to synthesize a summary
    formatted_prompt = f"Summarize the following search results for the query: '{query}'.\n\n{summary}"
    ollama_response = ollama_chat(
        model=configurable.query_generator_model,
        messages=[{"role": "user", "content": formatted_prompt}],
    )
    text = ollama_response["message"]["content"]
    # Insert citation markers (optional, simple version)
    for s in sources:
        text += f"\n[{s['label']}]({s['short_url']})"
    return {
        "sources_gathered": sources,
        "search_query": [query],
        "web_research_result": [text],
    }


def reflection(state: OverallState, config: RunnableConfig) -> ReflectionState:
    configurable = Configuration.from_runnable_config(config)
    state["research_loop_count"] = state.get("research_loop_count", 0) + 1
    reasoning_model = state.get("reasoning_model") or configurable.reflection_model
    current_date = get_current_date()
    formatted_prompt = reflection_instructions.format(
        current_date=current_date,
        research_topic=get_research_topic(state["messages"]),
        summaries="\n\n---\n\n".join(state["web_research_result"]),
    )
    response = ollama_chat(
        model=reasoning_model,
        messages=[{"role": "user", "content": formatted_prompt}],
    )
    import json
    import re
    content = response["message"]["content"]
    print("Ollama response:", content)  # Debug print
    try:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            result = json.loads(match.group(0))
        else:
            print("No JSON object found in Ollama response.")
            result = {"is_sufficient": False, "knowledge_gap": "", "follow_up_queries": []}
    except Exception as e:
        print(f"Error parsing Ollama response as JSON: {e}\nResponse was: {content}")
        result = {"is_sufficient": False, "knowledge_gap": "", "follow_up_queries": []}
    return {
        "is_sufficient": result.get("is_sufficient", False),
        "knowledge_gap": result.get("knowledge_gap", ""),
        "follow_up_queries": result.get("follow_up_queries", []),
        "research_loop_count": state["research_loop_count"],
        "number_of_ran_queries": len(state["search_query"]),
    }


def evaluate_research(
    state: ReflectionState,
    config: RunnableConfig,
) -> OverallState:
    configurable = Configuration.from_runnable_config(config)
    max_research_loops = (
        state.get("max_research_loops")
        if state.get("max_research_loops") is not None
        else configurable.max_research_loops
    )
    if state["is_sufficient"] or state["research_loop_count"] >= max_research_loops:
        return "finalize_answer"
    else:
        return [
            Send(
                "web_research",
                {
                    "search_query": follow_up_query,
                    "id": state["number_of_ran_queries"] + int(idx),
                },
            )
            for idx, follow_up_query in enumerate(state["follow_up_queries"])
        ]


def finalize_answer(state: OverallState, config: RunnableConfig):
    configurable = Configuration.from_runnable_config(config)
    reasoning_model = state.get("reasoning_model") or configurable.answer_model
    current_date = get_current_date()
    formatted_prompt = answer_instructions.format(
        current_date=current_date,
        research_topic=get_research_topic(state["messages"]),
        summaries="\n---\n\n".join(state["web_research_result"]),
    )
    response = ollama_chat(
        model=reasoning_model,
        messages=[{"role": "user", "content": formatted_prompt}],
    )
    text = response["message"]["content"]
    unique_sources = state["sources_gathered"]

    # Replace [Source N] with markdown links in the answer
    for source in unique_sources:
        label = source["label"]
        url = source["short_url"]
        text = text.replace(f"[{label}]", f"[{label}]({url})")

    return {
        "messages": [AIMessage(content=text)],
        "sources_gathered": unique_sources,
    }

# Create our Agent Graph
builder = StateGraph(OverallState, config_schema=Configuration)

builder.add_node("generate_query", generate_query)
builder.add_node("web_research", web_research)
builder.add_node("reflection", reflection)
builder.add_node("finalize_answer", finalize_answer)

builder.add_edge(START, "generate_query")
builder.add_conditional_edges(
    "generate_query", continue_to_web_research, ["web_research"]
)
builder.add_edge("web_research", "reflection")
builder.add_conditional_edges(
    "reflection", evaluate_research, ["web_research", "finalize_answer"]
)
builder.add_edge("finalize_answer", END)

graph = builder.compile(name="pro-search-agent")
