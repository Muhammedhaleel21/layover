"""LangGraph pipeline builder for adventure generation."""

from langgraph.graph import StateGraph, END, START
from .state import AdventureState
from .nodes import (
    fetch_places_node,
    analyze_constraints_node, 
    llm_curate_node,
    validate_and_assemble_node
)


def should_retry_llm(state: AdventureState) -> str:
    """
    Conditional edge to determine if LLM curation should be retried.
    
    Retries up to 2 times if there's an error and we haven't exceeded the limit.
    """
    error_count = state.get("error_count", 0)
    last_error = state.get("last_error")
    
    # Retry if we have an error and haven't exceeded retry limit
    if last_error and error_count <= 2:
        return "llm_curate"
    else:
        return "validate_and_assemble"


def build_adventure_graph() -> StateGraph:
    """Build the LangGraph pipeline for adventure generation."""
    
    # Create the graph
    graph = StateGraph(AdventureState)
    
    # Add nodes
    graph.add_node("fetch_places", fetch_places_node)
    graph.add_node("analyze_constraints", analyze_constraints_node) 
    graph.add_node("llm_curate", llm_curate_node)
    graph.add_node("validate_and_assemble", validate_and_assemble_node)
    
    # Add edges
    graph.add_edge(START, "fetch_places")
    graph.add_edge("fetch_places", "analyze_constraints")
    graph.add_edge("analyze_constraints", "llm_curate")
    
    # Conditional edge for LLM retry logic
    graph.add_conditional_edges(
        "llm_curate",
        should_retry_llm,
        {
            "llm_curate": "llm_curate",       # Retry LLM curation
            "validate_and_assemble": "validate_and_assemble"  # Continue to validation
        }
    )
    
    graph.add_edge("validate_and_assemble", END)
    
    return graph.compile()


# Create the compiled graph
adventure_graph = build_adventure_graph()