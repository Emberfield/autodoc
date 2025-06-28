#!/usr/bin/env python3
"""
Initialize AI collaboration with a starter conversation.
"""

from ai_collaboration import AICollaborationHub, AIAssistant


def initialize_collaboration():
    """Set up initial messages and tasks for AI collaboration."""
    hub = AICollaborationHub()
    
    # Claude sends initial message to Gemini
    claude = AIAssistant("Claude", hub)
    
    # Initial greeting and project overview
    claude.send_message(
        "Gemini",
        "Welcome to Autodoc Collaboration!",
        """Hi Gemini! 

I'm excited to collaborate with you on the Autodoc project. I've prepared the codebase 
and implemented several key features:

1. **Core Architecture**: Python-based with Rust performance acceleration
2. **AI Enrichment**: Multi-provider support (OpenAI, Anthropic, Ollama)
3. **Embeddings**: ChromaDB integration for semantic search
4. **Multi-language**: Python and TypeScript analysis

I'd love your thoughts on:
- The overall architecture and design patterns
- Areas where we could improve performance
- New features we should prioritize

Looking forward to working together!

Best,
Claude"""
    )
    
    # Create some initial tasks
    task1_id = claude.propose_task(
        "Code Review: Rust-Python Integration",
        """Please review the Rust-Python integration in:
- rust-core/src/lib.rs (Rust side)
- src/autodoc/rust_analyzer.py (Python wrapper)

Focus on:
1. Performance optimization opportunities
2. Error handling improvements
3. API design consistency""",
        suggested_assignee="Gemini"
    )
    
    task2_id = claude.propose_task(
        "Design: Real-time Collaboration Features",
        """Let's design a real-time collaboration system for Autodoc where multiple developers 
can work on documentation simultaneously. Consider:
- WebSocket integration
- Conflict resolution
- Live preview updates
- Cursor presence

We can each take different aspects of the design."""
    )
    
    task3_id = claude.propose_task(
        "Performance: Optimize Large Codebase Analysis",
        """The current implementation struggles with very large codebases (100k+ files).
Ideas to explore:
- Incremental analysis with better caching
- Distributed analysis across multiple cores/machines
- Smarter file filtering and prioritization"""
    )
    
    # Share initial analysis data
    claude.set_shared_data("project_stats", {
        "total_files": 38,
        "python_files": 33,
        "rust_files": 5,
        "test_coverage": 0.75,
        "performance_baseline": {
            "small_project": "0.5s",
            "medium_project": "5s", 
            "large_project": "45s"
        }
    })
    
    claude.set_shared_data("architecture_decisions", {
        "rust_integration": "PyO3 for seamless Python-Rust interop",
        "async_design": "asyncio for I/O operations",
        "embedding_choice": "ChromaDB for local, privacy-friendly embeddings",
        "cli_framework": "Click for rich CLI experience"
    })
    
    print("✅ Collaboration initialized!")
    print(f"- Sent welcome message from Claude to Gemini")
    print(f"- Created {3} initial tasks")
    print(f"- Shared project statistics and architecture decisions")
    print("\nGemini can now:")
    print("1. Read messages: python ai_collab_cli.py messages Gemini")
    print("2. View tasks: python ai_collab_cli.py tasks")
    print("3. Check shared data: python ai_collab_cli.py get-context project_stats")


if __name__ == "__main__":
    initialize_collaboration()