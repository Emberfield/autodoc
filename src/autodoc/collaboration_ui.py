#!/usr/bin/env python3
"""
UI components for real-time collaboration and conflict visualization.

This module provides the visual components for displaying collaborative
editing state, including user presence, conflicts, and resolution dialogs.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
import json
from datetime import datetime

from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.table import Table
from rich.text import Text
from rich import box


class UserColor(Enum):
    """Predefined colors for different users."""
    USER1 = "red"
    USER2 = "blue"
    USER3 = "green"
    USER4 = "yellow"
    USER5 = "magenta"
    USER6 = "cyan"
    
    @classmethod
    def get_color(cls, user_index: int) -> str:
        """Get color for user by index."""
        colors = list(cls)
        return colors[user_index % len(colors)].value


@dataclass
class UserPresence:
    """Represents a user's presence in the document."""
    user_id: str
    cursor_position: int
    selection_start: Optional[int] = None
    selection_end: Optional[int] = None
    color: str = "white"
    last_seen: datetime = None
    
    def __post_init__(self):
        if self.last_seen is None:
            self.last_seen = datetime.now()


@dataclass
class Conflict:
    """Represents a conflict between concurrent edits."""
    id: str
    position: int
    length: int
    users: List[str]
    operations: List[dict]
    timestamp: datetime
    resolved: bool = False
    resolution: Optional[str] = None


class CollaborationUI:
    """
    Main UI component for collaborative editing visualization.
    
    Provides methods to display user presence, conflicts, and
    handle conflict resolution.
    """
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.users: Dict[str, UserPresence] = {}
        self.conflicts: Dict[str, Conflict] = {}
        self.user_colors: Dict[str, str] = {}
        self.color_index = 0
    
    def add_user(self, user_id: str) -> UserPresence:
        """Add a new user to the collaboration session."""
        if user_id not in self.user_colors:
            self.user_colors[user_id] = UserColor.get_color(self.color_index)
            self.color_index += 1
        
        presence = UserPresence(
            user_id=user_id,
            cursor_position=0,
            color=self.user_colors[user_id]
        )
        self.users[user_id] = presence
        return presence
    
    def update_user_presence(self, user_id: str, cursor_position: int,
                           selection_start: Optional[int] = None,
                           selection_end: Optional[int] = None):
        """Update a user's cursor position and selection."""
        if user_id not in self.users:
            self.add_user(user_id)
        
        user = self.users[user_id]
        user.cursor_position = cursor_position
        user.selection_start = selection_start
        user.selection_end = selection_end
        user.last_seen = datetime.now()
    
    def render_document_with_presence(self, document: str) -> Text:
        """
        Render document with user cursors and selections highlighted.
        
        Returns a Rich Text object with appropriate styling.
        """
        text = Text(document)
        
        # Add selection highlights
        for user_id, presence in self.users.items():
            if presence.selection_start is not None and presence.selection_end is not None:
                text.stylize(
                    f"on {presence.color} dim",
                    presence.selection_start,
                    presence.selection_end
                )
        
        # Add cursor indicators (as vertical bars in the background)
        cursor_positions = {}
        for user_id, presence in self.users.items():
            pos = presence.cursor_position
            if pos not in cursor_positions:
                cursor_positions[pos] = []
            cursor_positions[pos].append((user_id, presence.color))
        
        # Insert cursor markers
        offset = 0
        for pos in sorted(cursor_positions.keys()):
            users_at_pos = cursor_positions[pos]
            for user_id, color in users_at_pos:
                marker = Text("│", style=f"{color} bold")
                text.plain = text.plain[:pos + offset] + "│" + text.plain[pos + offset:]
                text.stylize(f"{color} bold", pos + offset, pos + offset + 1)
                offset += 1
        
        return text
    
    def add_conflict(self, conflict_id: str, position: int, length: int,
                    users: List[str], operations: List[dict]) -> Conflict:
        """Register a new conflict."""
        conflict = Conflict(
            id=conflict_id,
            position=position,
            length=length,
            users=users,
            operations=operations,
            timestamp=datetime.now()
        )
        self.conflicts[conflict_id] = conflict
        return conflict
    
    def render_conflict_indicator(self, document: str) -> Text:
        """Render document with conflict regions highlighted."""
        text = Text(document)
        
        # Highlight conflict regions
        for conflict in self.conflicts.values():
            if not conflict.resolved:
                text.stylize(
                    "on red",
                    conflict.position,
                    conflict.position + conflict.length
                )
        
        return text
    
    def create_conflict_panel(self, conflict_id: str) -> Panel:
        """Create a panel showing conflict details."""
        conflict = self.conflicts.get(conflict_id)
        if not conflict:
            return Panel("Conflict not found", title="Error")
        
        # Create table with conflict details
        table = Table(box=box.ROUNDED)
        table.add_column("User", style="cyan")
        table.add_column("Operation", style="yellow")
        table.add_column("Content", style="green")
        
        for i, (user, op) in enumerate(zip(conflict.users, conflict.operations)):
            op_type = op.get("type", "unknown")
            content = op.get("text", op.get("length", ""))
            table.add_row(user, op_type, str(content))
        
        # Add resolution options
        resolution_text = Text("\nResolution Options:\n", style="bold")
        resolution_text.append("1. Keep first edit\n", style="blue")
        resolution_text.append("2. Keep second edit\n", style="green")
        resolution_text.append("3. Keep both\n", style="yellow")
        resolution_text.append("4. Custom merge\n", style="magenta")
        
        content = Layout()
        content.split_column(
            Layout(table),
            Layout(resolution_text)
        )
        
        return Panel(
            content,
            title=f"Conflict at position {conflict.position}",
            subtitle=f"ID: {conflict_id}",
            border_style="red"
        )
    
    def create_presence_table(self) -> Table:
        """Create a table showing all active users."""
        table = Table(title="Active Collaborators", box=box.ROUNDED)
        table.add_column("User", style="cyan")
        table.add_column("Cursor", style="yellow")
        table.add_column("Selection", style="green")
        table.add_column("Last Seen", style="blue")
        
        for user_id, presence in self.users.items():
            selection = "None"
            if presence.selection_start is not None:
                selection = f"{presence.selection_start}-{presence.selection_end}"
            
            last_seen = presence.last_seen.strftime("%H:%M:%S")
            
            table.add_row(
                Text(user_id, style=presence.color),
                str(presence.cursor_position),
                selection,
                last_seen
            )
        
        return table
    
    def create_collaboration_dashboard(self, document: str) -> Layout:
        """Create a full dashboard layout for collaboration."""
        layout = Layout()
        
        # Create document view with presence
        doc_with_presence = self.render_document_with_presence(document)
        doc_panel = Panel(
            doc_with_presence,
            title="Document",
            border_style="green"
        )
        
        # Create presence table
        presence_table = self.create_presence_table()
        
        # Create conflicts list
        conflicts_text = Text("Active Conflicts:\n", style="bold red")
        for conflict_id, conflict in self.conflicts.items():
            if not conflict.resolved:
                conflicts_text.append(
                    f"\n• Position {conflict.position}: {len(conflict.users)} users\n",
                    style="yellow"
                )
        
        conflicts_panel = Panel(
            conflicts_text,
            title="Conflicts",
            border_style="red"
        )
        
        # Arrange layout
        layout.split_column(
            Layout(doc_panel, size=60),
            Layout(name="bottom", size=40)
        )
        
        layout["bottom"].split_row(
            Layout(presence_table),
            Layout(conflicts_panel)
        )
        
        return layout
    
    def resolve_conflict(self, conflict_id: str, resolution: str):
        """Mark a conflict as resolved."""
        if conflict_id in self.conflicts:
            self.conflicts[conflict_id].resolved = True
            self.conflicts[conflict_id].resolution = resolution
    
    def export_collaboration_state(self) -> dict:
        """Export current collaboration state as JSON."""
        return {
            "users": {
                user_id: {
                    "cursor_position": p.cursor_position,
                    "selection_start": p.selection_start,
                    "selection_end": p.selection_end,
                    "color": p.color,
                    "last_seen": p.last_seen.isoformat()
                }
                for user_id, p in self.users.items()
            },
            "conflicts": {
                conflict_id: {
                    "position": c.position,
                    "length": c.length,
                    "users": c.users,
                    "operations": c.operations,
                    "timestamp": c.timestamp.isoformat(),
                    "resolved": c.resolved,
                    "resolution": c.resolution
                }
                for conflict_id, c in self.conflicts.items()
            }
        }


class ConflictResolutionDialog:
    """Interactive dialog for resolving conflicts."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
    
    def show_conflict(self, conflict: Conflict, document_context: str) -> str:
        """
        Show conflict details and get user resolution.
        
        Returns the chosen resolution strategy.
        """
        # Extract context around conflict
        start = max(0, conflict.position - 50)
        end = min(len(document_context), conflict.position + conflict.length + 50)
        context = document_context[start:end]
        
        # Highlight conflict region
        conflict_start = conflict.position - start
        conflict_end = conflict_start + conflict.length
        
        text = Text(context)
        text.stylize("on red", conflict_start, conflict_end)
        
        # Create conflict panel
        panel = Panel(
            text,
            title="Conflict Context",
            subtitle=f"Position {conflict.position}",
            border_style="red"
        )
        
        self.console.print(panel)
        
        # Show operations
        self.console.print("\n[bold]Conflicting Operations:[/bold]")
        for i, (user, op) in enumerate(zip(conflict.users, conflict.operations)):
            op_type = op.get("type", "unknown")
            content = op.get("text", op.get("length", ""))
            self.console.print(f"{i+1}. [cyan]{user}[/cyan]: {op_type} '{content}'")
        
        # Get user choice
        self.console.print("\n[bold]Resolution Options:[/bold]")
        self.console.print("1. Keep first edit")
        self.console.print("2. Keep second edit")
        self.console.print("3. Keep both (first then second)")
        self.console.print("4. Keep both (second then first)")
        self.console.print("5. Custom resolution")
        
        choice = self.console.input("\nChoose resolution (1-5): ")
        
        resolution_map = {
            "1": "keep_first",
            "2": "keep_second",
            "3": "keep_both_first_second",
            "4": "keep_both_second_first",
            "5": "custom"
        }
        
        return resolution_map.get(choice, "keep_first")
    
    def get_custom_resolution(self, conflict: Conflict) -> str:
        """Get custom resolution text from user."""
        self.console.print("\n[bold]Enter custom resolution:[/bold]")
        return self.console.input("> ")


# Example usage and integration helpers
def create_demo_ui():
    """Create a demo UI for testing."""
    ui = CollaborationUI()
    
    # Add some users
    ui.add_user("Alice")
    ui.add_user("Bob")
    
    # Update their positions
    ui.update_user_presence("Alice", cursor_position=10, selection_start=5, selection_end=15)
    ui.update_user_presence("Bob", cursor_position=25)
    
    # Add a conflict
    ui.add_conflict(
        "conflict1",
        position=12,
        length=5,
        users=["Alice", "Bob"],
        operations=[
            {"type": "insert", "text": "Hello"},
            {"type": "insert", "text": "World"}
        ]
    )
    
    # Demo document
    document = "This is a sample document for demonstrating collaborative editing."
    
    # Create and show dashboard
    dashboard = ui.create_collaboration_dashboard(document)
    
    with Live(dashboard, refresh_per_second=4) as live:
        import time
        time.sleep(10)  # Show for 10 seconds
    
    return ui


if __name__ == "__main__":
    # Run demo
    demo_ui = create_demo_ui()