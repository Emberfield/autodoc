#!/usr/bin/env python3
"""
CLI for AI Collaboration System
Allows manual interaction with the AI collaboration hub.
"""

import click
import json
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

from ai_collaboration import AICollaborationHub, AIAssistant, MessageStatus, TaskStatus

console = Console()


@click.group()
def cli():
    """AI Collaboration CLI - Manage messages and tasks between AI assistants."""
    pass


@cli.command()
@click.option('--from', 'sender', required=True, help='Sender name (e.g., Claude, Gemini)')
@click.option('--to', 'recipient', required=True, help='Recipient name')
@click.option('--subject', required=True, help='Message subject')
@click.option('--content', required=True, help='Message content')
def send(sender, recipient, subject, content):
    """Send a message between AIs."""
    hub = AICollaborationHub()
    ai = AIAssistant(sender, hub)
    
    msg_id = ai.send_message(recipient, subject, content)
    console.print(f"[green]✓ Message sent![/green] (ID: {msg_id})")
    console.print(f"From: {sender} → To: {recipient}")
    console.print(f"Subject: {subject}")


@cli.command()
@click.argument('recipient')
@click.option('--unread', is_flag=True, help='Show only unread messages')
def messages(recipient, unread):
    """Check messages for a specific AI."""
    hub = AICollaborationHub()
    
    if unread:
        messages = hub.get_messages(recipient, MessageStatus.PENDING)
    else:
        messages = hub.get_messages(recipient)
    
    if not messages:
        console.print(f"[yellow]No messages for {recipient}[/yellow]")
        return
    
    table = Table(title=f"Messages for {recipient}")
    table.add_column("ID", style="cyan")
    table.add_column("From", style="blue")
    table.add_column("Subject", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Date", style="dim")
    
    for msg in messages:
        table.add_row(
            str(msg.id),
            msg.sender,
            msg.subject,
            msg.status,
            msg.created_at or "Unknown"
        )
    
    console.print(table)


@cli.command()
@click.argument('message_id', type=int)
def read(message_id):
    """Read a specific message."""
    hub = AICollaborationHub()
    conn = hub._init_database() or hub.db_path
    
    import sqlite3
    conn = sqlite3.connect(hub.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
    row = cursor.fetchone()
    
    if not row:
        console.print(f"[red]Message {message_id} not found[/red]")
        return
    
    # Mark as read
    hub.mark_message_read(message_id)
    
    # Display message
    panel = Panel(
        f"[bold]From:[/bold] {row['sender']}\n"
        f"[bold]To:[/bold] {row['recipient']}\n"
        f"[bold]Subject:[/bold] {row['subject']}\n"
        f"[bold]Date:[/bold] {row['created_at']}\n\n"
        f"{row['content']}",
        title=f"Message #{message_id}",
        border_style="blue"
    )
    console.print(panel)
    
    conn.close()


@cli.command()
@click.option('--title', required=True, help='Task title')
@click.option('--description', required=True, help='Task description')
@click.option('--created-by', required=True, help='Creator name')
@click.option('--assign-to', help='Suggested assignee')
def create_task(title, description, created_by, assign_to):
    """Create a new task."""
    hub = AICollaborationHub()
    
    task_id = hub.create_task(title, description, created_by, assign_to)
    console.print(f"[green]✓ Task created![/green] (ID: {task_id})")
    console.print(f"Title: {title}")
    if assign_to:
        console.print(f"Suggested assignee: {assign_to}")


@cli.command()
@click.option('--assignee', help='Filter by assignee')
@click.option('--status', type=click.Choice(['proposed', 'accepted', 'in_progress', 'completed', 'blocked']))
def tasks(assignee, status):
    """List tasks."""
    hub = AICollaborationHub()
    
    status_enum = TaskStatus(status) if status else None
    task_list = hub.get_tasks(assignee, status_enum)
    
    if not task_list:
        console.print("[yellow]No tasks found[/yellow]")
        return
    
    table = Table(title="Tasks")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("Assignee", style="blue")
    table.add_column("Status", style="yellow")
    table.add_column("Created By", style="dim")
    
    for task in task_list:
        table.add_row(
            str(task.id),
            task.title,
            task.assignee or "Unassigned",
            task.status,
            task.created_by
        )
    
    console.print(table)


@cli.command()
@click.argument('task_id', type=int)
@click.argument('status', type=click.Choice(['accepted', 'in_progress', 'completed', 'blocked']))
@click.option('--assignee', help='Assign to specific AI')
def update_task(task_id, status, assignee):
    """Update task status."""
    hub = AICollaborationHub()
    
    status_enum = TaskStatus(status)
    hub.update_task_status(task_id, status_enum, assignee)
    
    console.print(f"[green]✓ Task {task_id} updated![/green]")
    console.print(f"New status: {status}")
    if assignee:
        console.print(f"Assigned to: {assignee}")


@cli.command()
@click.argument('thread_id')
def thread(thread_id):
    """View all messages in a thread."""
    hub = AICollaborationHub()
    messages = hub.get_thread_messages(thread_id)
    
    if not messages:
        console.print(f"[yellow]No messages in thread {thread_id}[/yellow]")
        return
    
    console.print(f"\n[bold]Thread: {thread_id}[/bold]\n")
    
    for msg in messages:
        timestamp = msg.created_at or "Unknown"
        console.print(f"[dim]{timestamp}[/dim] [blue]{msg.sender}[/blue] → [green]{msg.recipient}[/green]")
        console.print(f"[bold]{msg.subject}[/bold]")
        console.print(msg.content)
        console.print("─" * 50)


@cli.command()
@click.argument('key')
@click.argument('value')
@click.option('--ai', required=True, help='AI setting the value')
def set_context(key, value, ai):
    """Set shared context value."""
    hub = AICollaborationHub()
    
    # Try to parse as JSON
    try:
        parsed_value = json.loads(value)
    except json.JSONDecodeError:
        parsed_value = value
    
    hub.set_context(key, parsed_value, ai)
    console.print(f"[green]✓ Context set![/green]")
    console.print(f"Key: {key}")
    console.print(f"Set by: {ai}")


@cli.command()
@click.argument('key')
def get_context(key):
    """Get shared context value."""
    hub = AICollaborationHub()
    value = hub.get_context(key)
    
    if value is None:
        console.print(f"[yellow]No value found for key: {key}[/yellow]")
    else:
        console.print(f"[bold]Key:[/bold] {key}")
        console.print(f"[bold]Value:[/bold]")
        if isinstance(value, (dict, list)):
            console.print(json.dumps(value, indent=2))
        else:
            console.print(value)


@cli.command()
def status():
    """Show collaboration hub status."""
    hub = AICollaborationHub()
    
    # Count messages
    import sqlite3
    conn = sqlite3.connect(hub.db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM messages")
    total_messages = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM messages WHERE status = ?", (MessageStatus.PENDING.value,))
    unread_messages = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM tasks")
    total_tasks = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status != ?", (TaskStatus.COMPLETED.value,))
    open_tasks = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM shared_context")
    context_items = cursor.fetchone()[0]
    
    conn.close()
    
    # Display status
    panel = Panel(
        f"[bold]Messages:[/bold] {total_messages} total, {unread_messages} unread\n"
        f"[bold]Tasks:[/bold] {total_tasks} total, {open_tasks} open\n"
        f"[bold]Shared Context:[/bold] {context_items} items\n"
        f"[bold]Database:[/bold] {hub.db_path}",
        title="AI Collaboration Hub Status",
        border_style="green"
    )
    console.print(panel)


if __name__ == "__main__":
    cli()