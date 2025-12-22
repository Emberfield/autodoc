#!/usr/bin/env python3
"""
Demo script for the collaborative editing UI components.

Run this to see the collaboration UI in action with simulated users.
"""

import asyncio
import random
from datetime import datetime
from rich.console import Console
from rich.live import Live

from autodoc.collaboration_ui import CollaborationUI, ConflictResolutionDialog


async def simulate_collaboration():
    """Simulate a collaborative editing session."""
    console = Console()
    ui = CollaborationUI(console)
    
    # Sample document
    document = """# Autodoc Real-time Collaboration

This is a demonstration of the real-time collaborative editing features.

## Features
- Multiple user cursors
- Conflict detection
- Live presence tracking
- Automatic conflict resolution

## How it works
The system uses Operational Transformation (OT) to handle concurrent edits."""
    
    # Add users
    users = ["Alice", "Bob", "Charlie"]
    for user in users:
        ui.add_user(user)
    
    console.print("[bold green]Starting collaboration simulation...[/bold green]\n")
    
    # Create live display
    with Live(ui.create_collaboration_dashboard(document), refresh_per_second=2) as live:
        # Simulate user movements
        for i in range(20):
            # Random user actions
            user = random.choice(users)
            action = random.choice(["move_cursor", "select", "create_conflict"])
            
            if action == "move_cursor":
                position = random.randint(0, len(document) - 1)
                ui.update_user_presence(user, cursor_position=position)
            
            elif action == "select":
                start = random.randint(0, len(document) - 20)
                end = start + random.randint(5, 20)
                ui.update_user_presence(
                    user, 
                    cursor_position=end,
                    selection_start=start,
                    selection_end=end
                )
            
            elif action == "create_conflict" and i > 5:  # Only after some time
                # Simulate a conflict
                position = random.randint(50, 150)
                conflict_users = random.sample(users, 2)
                ui.add_conflict(
                    f"conflict_{i}",
                    position=position,
                    length=10,
                    users=conflict_users,
                    operations=[
                        {"type": "insert", "text": f"Edit by {conflict_users[0]}"},
                        {"type": "insert", "text": f"Edit by {conflict_users[1]}"}
                    ]
                )
            
            # Update display
            live.update(ui.create_collaboration_dashboard(document))
            await asyncio.sleep(0.5)
    
    # Show conflict resolution
    if ui.conflicts:
        console.print("\n[bold red]Conflicts detected![/bold red]")
        dialog = ConflictResolutionDialog(console)
        
        for conflict_id, conflict in ui.conflicts.items():
            if not conflict.resolved:
                console.print(f"\n[yellow]Resolving conflict {conflict_id}...[/yellow]")
                resolution = dialog.show_conflict(conflict, document)
                ui.resolve_conflict(conflict_id, resolution)
                console.print(f"[green]Conflict resolved: {resolution}[/green]")
    
    # Export final state
    state = ui.export_collaboration_state()
    console.print("\n[bold]Final collaboration state:[/bold]")
    console.print_json(data=state)


def main():
    """Run the collaboration demo."""
    console = Console()
    
    console.print("""
[bold cyan]Autodoc Collaborative Editing Demo[/bold cyan]
[dim]This demonstrates the UI components for real-time collaboration[/dim]
    """)
    
    try:
        asyncio.run(simulate_collaboration())
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted by user[/yellow]")


if __name__ == "__main__":
    main()