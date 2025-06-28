#!/usr/bin/env python3
"""
AI Collaboration System - Asynchronous communication between AI assistants
Allows Claude and Gemini to collaborate on code through a message queue system.
"""

import json
import sqlite3
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any
import hashlib


class MessageStatus(Enum):
    PENDING = "pending"
    READ = "read"
    REPLIED = "replied"
    WORKING = "working"


class TaskStatus(Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


@dataclass
class Message:
    id: Optional[int] = None
    sender: str = ""
    recipient: str = ""
    subject: str = ""
    content: str = ""
    status: str = MessageStatus.PENDING.value
    created_at: Optional[str] = None
    read_at: Optional[str] = None
    thread_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class Task:
    id: Optional[int] = None
    title: str = ""
    description: str = ""
    assignee: Optional[str] = None
    status: str = TaskStatus.PROPOSED.value
    created_by: str = ""
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    dependencies: Optional[List[int]] = None
    metadata: Optional[Dict[str, Any]] = None


class AICollaborationHub:
    """Central hub for AI assistant collaboration."""
    
    def __init__(self, db_path: str = "ai_collaboration.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                recipient TEXT NOT NULL,
                subject TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                read_at TIMESTAMP,
                thread_id TEXT,
                metadata TEXT
            )
        """)
        
        # Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                assignee TEXT,
                status TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                dependencies TEXT,
                metadata TEXT
            )
        """)
        
        # Shared context table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shared_context (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def send_message(self, sender: str, recipient: str, subject: str, content: str, 
                     thread_id: Optional[str] = None, metadata: Optional[Dict] = None) -> int:
        """Send a message from one AI to another."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if thread_id is None and subject:
            # Generate thread ID from subject
            thread_id = hashlib.md5(subject.encode()).hexdigest()[:8]
        
        cursor.execute("""
            INSERT INTO messages (sender, recipient, subject, content, status, thread_id, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (sender, recipient, subject, content, MessageStatus.PENDING.value, 
              thread_id, json.dumps(metadata) if metadata else None))
        
        message_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return message_id
    
    def get_messages(self, recipient: str, status: Optional[MessageStatus] = None) -> List[Message]:
        """Get messages for a specific recipient."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if status:
            cursor.execute("""
                SELECT * FROM messages 
                WHERE recipient = ? AND status = ?
                ORDER BY created_at DESC
            """, (recipient, status.value))
        else:
            cursor.execute("""
                SELECT * FROM messages 
                WHERE recipient = ?
                ORDER BY created_at DESC
            """, (recipient,))
        
        messages = []
        for row in cursor.fetchall():
            msg = Message(
                id=row['id'],
                sender=row['sender'],
                recipient=row['recipient'],
                subject=row['subject'],
                content=row['content'],
                status=row['status'],
                created_at=row['created_at'],
                read_at=row['read_at'],
                thread_id=row['thread_id'],
                metadata=json.loads(row['metadata']) if row['metadata'] else None
            )
            messages.append(msg)
        
        conn.close()
        return messages
    
    def mark_message_read(self, message_id: int):
        """Mark a message as read."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE messages 
            SET status = ?, read_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (MessageStatus.READ.value, message_id))
        
        conn.commit()
        conn.close()
    
    def create_task(self, title: str, description: str, created_by: str,
                    assignee: Optional[str] = None, dependencies: Optional[List[int]] = None,
                    metadata: Optional[Dict] = None) -> int:
        """Create a new task."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO tasks (title, description, assignee, status, created_by, dependencies, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (title, description, assignee, TaskStatus.PROPOSED.value, created_by,
              json.dumps(dependencies) if dependencies else None,
              json.dumps(metadata) if metadata else None))
        
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return task_id
    
    def get_tasks(self, assignee: Optional[str] = None, status: Optional[TaskStatus] = None) -> List[Task]:
        """Get tasks, optionally filtered by assignee and/or status."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []
        
        if assignee:
            query += " AND assignee = ?"
            params.append(assignee)
        
        if status:
            query += " AND status = ?"
            params.append(status.value)
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        
        tasks = []
        for row in cursor.fetchall():
            task = Task(
                id=row['id'],
                title=row['title'],
                description=row['description'],
                assignee=row['assignee'],
                status=row['status'],
                created_by=row['created_by'],
                created_at=row['created_at'],
                completed_at=row['completed_at'],
                dependencies=json.loads(row['dependencies']) if row['dependencies'] else None,
                metadata=json.loads(row['metadata']) if row['metadata'] else None
            )
            tasks.append(task)
        
        conn.close()
        return tasks
    
    def update_task_status(self, task_id: int, status: TaskStatus, assignee: Optional[str] = None):
        """Update task status and optionally assign it."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if assignee:
            cursor.execute("""
                UPDATE tasks 
                SET status = ?, assignee = ?
                WHERE id = ?
            """, (status.value, assignee, task_id))
        else:
            cursor.execute("""
                UPDATE tasks 
                SET status = ?
                WHERE id = ?
            """, (status.value, task_id))
        
        if status == TaskStatus.COMPLETED:
            cursor.execute("""
                UPDATE tasks 
                SET completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (task_id,))
        
        conn.commit()
        conn.close()
    
    def set_context(self, key: str, value: Any, updated_by: str):
        """Set shared context that both AIs can access."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        value_str = json.dumps(value) if not isinstance(value, str) else value
        
        cursor.execute("""
            INSERT OR REPLACE INTO shared_context (key, value, updated_at, updated_by)
            VALUES (?, ?, CURRENT_TIMESTAMP, ?)
        """, (key, value_str, updated_by))
        
        conn.commit()
        conn.close()
    
    def get_context(self, key: str) -> Optional[Any]:
        """Get shared context value."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT value FROM shared_context WHERE key = ?", (key,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            try:
                return json.loads(row[0])
            except json.JSONDecodeError:
                return row[0]
        return None
    
    def get_thread_messages(self, thread_id: str) -> List[Message]:
        """Get all messages in a thread."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM messages 
            WHERE thread_id = ?
            ORDER BY created_at ASC
        """, (thread_id,))
        
        messages = []
        for row in cursor.fetchall():
            msg = Message(
                id=row['id'],
                sender=row['sender'],
                recipient=row['recipient'],
                subject=row['subject'],
                content=row['content'],
                status=row['status'],
                created_at=row['created_at'],
                read_at=row['read_at'],
                thread_id=row['thread_id'],
                metadata=json.loads(row['metadata']) if row['metadata'] else None
            )
            messages.append(msg)
        
        conn.close()
        return messages


class AIAssistant:
    """Base class for AI assistants using the collaboration hub."""
    
    def __init__(self, name: str, hub: AICollaborationHub):
        self.name = name
        self.hub = hub
    
    def check_messages(self) -> List[Message]:
        """Check for new messages."""
        return self.hub.get_messages(self.name, MessageStatus.PENDING)
    
    def send_message(self, to: str, subject: str, content: str, 
                     thread_id: Optional[str] = None) -> int:
        """Send a message to another AI."""
        return self.hub.send_message(self.name, to, subject, content, thread_id)
    
    def reply_to_message(self, original_message: Message, content: str) -> int:
        """Reply to a message in the same thread."""
        return self.hub.send_message(
            self.name, 
            original_message.sender,
            f"Re: {original_message.subject}",
            content,
            original_message.thread_id
        )
    
    def propose_task(self, title: str, description: str, 
                     suggested_assignee: Optional[str] = None) -> int:
        """Propose a new task."""
        return self.hub.create_task(title, description, self.name, suggested_assignee)
    
    def check_tasks(self) -> List[Task]:
        """Check tasks assigned to me or unassigned."""
        my_tasks = self.hub.get_tasks(assignee=self.name)
        unassigned = self.hub.get_tasks(assignee=None, status=TaskStatus.PROPOSED)
        return my_tasks + unassigned
    
    def accept_task(self, task_id: int):
        """Accept a task."""
        self.hub.update_task_status(task_id, TaskStatus.ACCEPTED, self.name)
    
    def start_task(self, task_id: int):
        """Mark task as in progress."""
        self.hub.update_task_status(task_id, TaskStatus.IN_PROGRESS, self.name)
    
    def complete_task(self, task_id: int):
        """Mark task as completed."""
        self.hub.update_task_status(task_id, TaskStatus.COMPLETED)
    
    def set_shared_data(self, key: str, value: Any):
        """Set shared data for other AI to access."""
        self.hub.set_context(key, value, self.name)
    
    def get_shared_data(self, key: str) -> Optional[Any]:
        """Get shared data."""
        return self.hub.get_context(key)


# Example usage functions
def claude_example():
    """Example of Claude using the system."""
    hub = AICollaborationHub()
    claude = AIAssistant("Claude", hub)
    
    # Check for messages
    messages = claude.check_messages()
    for msg in messages:
        print(f"New message from {msg.sender}: {msg.subject}")
        claude.hub.mark_message_read(msg.id)
        
        # Analyze and reply
        if "code review" in msg.subject.lower():
            claude.reply_to_message(msg, 
                "I've reviewed the code. Here are my findings:\n"
                "1. The architecture looks solid\n"
                "2. Consider adding more error handling in the API layer\n"
                "3. The Rust integration is impressive!"
            )
    
    # Propose a task
    claude.propose_task(
        "Implement API rate limiting",
        "We should add rate limiting to prevent API abuse. "
        "I can handle the Python side if you want to do the Rust implementation.",
        suggested_assignee="Gemini"
    )
    
    # Share analysis results
    claude.set_shared_data("code_analysis", {
        "total_functions": 487,
        "test_coverage": 0.82,
        "complexity_hotspots": ["src/autodoc/analyzer.py", "src/autodoc/enrichment.py"]
    })


def gemini_example():
    """Example of Gemini using the system."""
    hub = AICollaborationHub()
    gemini = AIAssistant("Gemini", hub)
    
    # Check tasks
    tasks = gemini.check_tasks()
    for task in tasks:
        if task.status == TaskStatus.PROPOSED.value and "rate limiting" in task.title:
            print(f"Accepting task: {task.title}")
            gemini.accept_task(task.id)
            gemini.start_task(task.id)
            
            # Do work...
            time.sleep(1)  # Simulate work
            
            # Update progress
            gemini.send_message("Claude", 
                "Rate limiting implementation progress",
                "I've implemented the Rust side of rate limiting. "
                "It uses a token bucket algorithm for efficiency. "
                "Ready to integrate with your Python implementation!"
            )
    
    # Check shared data
    analysis = gemini.get_shared_data("code_analysis")
    if analysis:
        print(f"Code analysis shows {analysis['test_coverage']*100:.0f}% test coverage")


if __name__ == "__main__":
    # Initialize the hub
    hub = AICollaborationHub()
    
    print("AI Collaboration Hub initialized!")
    print(f"Database: {hub.db_path}")
    print("\nExample usage:")
    print("- Claude can run: claude_example()")
    print("- Gemini can run: gemini_example()")
    print("\nThe AIs can now collaborate asynchronously!")