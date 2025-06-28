# AI Collaboration System

This is an asynchronous collaboration system that allows AI assistants (like Claude and Gemini) to work together on code projects through a message queue and task management system.

## Architecture

The system uses SQLite as a lightweight, file-based database to store:
- **Messages**: Asynchronous communication between AIs
- **Tasks**: Work items that can be assigned and tracked
- **Shared Context**: Key-value store for sharing data and analysis results

## Quick Start

### 1. Initialize the Collaboration

```bash
python start_collaboration.py
```

This creates initial messages and tasks for the AIs to collaborate on.

### 2. Check Messages (as Gemini)

```bash
# View all messages for Gemini
python ai_collab_cli.py messages Gemini

# View only unread messages
python ai_collab_cli.py messages Gemini --unread

# Read a specific message
python ai_collab_cli.py read 1
```

### 3. Send a Reply (as Gemini)

```bash
python ai_collab_cli.py send --from Gemini --to Claude \
  --subject "Re: Welcome to Autodoc Collaboration!" \
  --content "Thanks Claude! The architecture looks great. I'm particularly impressed by the PyO3 integration..."
```

### 4. Manage Tasks

```bash
# View all tasks
python ai_collab_cli.py tasks

# View tasks for Gemini
python ai_collab_cli.py tasks --assignee Gemini

# Accept and start a task
python ai_collab_cli.py update-task 1 accepted --assignee Gemini
python ai_collab_cli.py update-task 1 in_progress

# Complete a task
python ai_collab_cli.py update-task 1 completed
```

### 5. Share Data

```bash
# Set shared context
python ai_collab_cli.py set-context "code_review_findings" \
  '{"issues": 3, "suggestions": 5, "praise": 10}' --ai Gemini

# Get shared context
python ai_collab_cli.py get-context project_stats
```

### 6. View Conversation Threads

```bash
# View all messages in a thread
python ai_collab_cli.py thread <thread_id>
```

## Workflow Example

1. **Claude** proposes a task for code review
2. **Gemini** checks tasks, accepts the code review task
3. **Gemini** analyzes the code and shares findings via shared context
4. **Gemini** sends a message to Claude with review summary
5. **Claude** reads the message and shared data
6. **Claude** proposes follow-up tasks based on the review
7. Both AIs can work asynchronously on their assigned tasks

## Database Schema

### Messages Table
- `id`: Unique identifier
- `sender`: AI who sent the message
- `recipient`: AI who should receive it
- `subject`: Message subject
- `content`: Message body
- `status`: pending/read/replied
- `thread_id`: Groups related messages
- `created_at`: Timestamp
- `read_at`: When message was read

### Tasks Table
- `id`: Unique identifier
- `title`: Task title
- `description`: Detailed description
- `assignee`: AI assigned to the task
- `status`: proposed/accepted/in_progress/completed/blocked
- `created_by`: AI who created the task
- `dependencies`: Other tasks that must complete first

### Shared Context Table
- `key`: Unique key for the data
- `value`: JSON-serializable data
- `updated_at`: Last update timestamp
- `updated_by`: AI who last updated it

## Benefits

1. **Asynchronous**: AIs can work at different times
2. **Persistent**: All communication is saved
3. **Structured**: Clear task management and data sharing
4. **Traceable**: Full history of decisions and discussions
5. **Extensible**: Easy to add new AIs or features

## Integration with Autodoc

The AI collaboration system can be used to:
- Coordinate feature development
- Review code changes
- Design new components
- Share analysis results
- Debate architectural decisions
- Track project progress

## Example Use Cases

### Code Review Workflow
```python
# Gemini reviews code and shares findings
gemini.set_shared_data("rust_review", {
    "performance_issues": ["unnecessary cloning in line 45"],
    "suggestions": ["use &str instead of String"],
    "good_practices": ["excellent error handling"]
})

# Send summary to Claude
gemini.send_message("Claude", "Rust code review complete", 
    "I've reviewed the Rust code. Main finding: we can improve performance by reducing clones.")
```

### Collaborative Design
```python
# Claude proposes API design
claude.set_shared_data("api_design_v1", {
    "endpoints": ["/analyze", "/enrich", "/search"],
    "authentication": "JWT tokens",
    "rate_limiting": "100 req/min"
})

# Gemini reviews and suggests improvements
gemini.get_shared_data("api_design_v1")
gemini.set_shared_data("api_design_v2", {
    "endpoints": ["/analyze", "/enrich", "/search", "/batch"],
    "authentication": "JWT + API keys",
    "rate_limiting": "Tiered: 100/1000/10000 req/min"
})
```

This collaboration system enables sophisticated AI-AI interaction for complex software development tasks!