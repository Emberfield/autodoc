#!/usr/bin/env python3
"""
Operational Transformation (OT) engine for real-time collaborative editing.

This module implements the core OT algorithm for transforming concurrent text
operations to maintain consistency across multiple clients.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple, Union
import logging

log = logging.getLogger(__name__)


class OpType(Enum):
    """Types of text operations."""
    INSERT = "insert"
    DELETE = "delete"
    RETAIN = "retain"  # Skip characters without modification


@dataclass
class Operation(ABC):
    """Base class for all text operations."""
    position: int
    client_id: str
    version: int
    
    @abstractmethod
    def apply(self, text: str) -> str:
        """Apply this operation to the given text."""
        pass
    
    @abstractmethod
    def transform(self, other: 'Operation', priority: bool = False) -> 'Operation':
        """Transform this operation against another concurrent operation."""
        pass
    
    @abstractmethod
    def invert(self) -> 'Operation':
        """Create an inverse operation that undoes this operation."""
        pass


@dataclass
class InsertOp(Operation):
    """Insert text at a specific position."""
    text: str
    
    def apply(self, document: str) -> str:
        """Insert text into the document."""
        return document[:self.position] + self.text + document[self.position:]
    
    def transform(self, other: Operation, priority: bool = False) -> Operation:
        """Transform this insert against another operation."""
        if isinstance(other, InsertOp):
            if self.position < other.position:
                # This insert happens before the other
                return self
            elif self.position > other.position:
                # This insert happens after the other, adjust position
                return InsertOp(
                    position=self.position + len(other.text),
                    text=self.text,
                    client_id=self.client_id,
                    version=self.version
                )
            else:
                # Same position - use priority to determine order
                if priority:
                    return self
                else:
                    return InsertOp(
                        position=self.position + len(other.text),
                        text=self.text,
                        client_id=self.client_id,
                        version=self.version
                    )
        
        elif isinstance(other, DeleteOp):
            if self.position <= other.position:
                # Insert happens before or at delete position
                return self
            elif self.position > other.position + other.length:
                # Insert happens after deleted range
                return InsertOp(
                    position=self.position - other.length,
                    text=self.text,
                    client_id=self.client_id,
                    version=self.version
                )
            else:
                # Insert happens within deleted range
                return InsertOp(
                    position=other.position,
                    text=self.text,
                    client_id=self.client_id,
                    version=self.version
                )
        
        return self
    
    def invert(self) -> 'DeleteOp':
        """Create a delete operation that undoes this insert."""
        return DeleteOp(
            position=self.position,
            length=len(self.text),
            client_id=self.client_id,
            version=self.version + 1
        )


@dataclass
class DeleteOp(Operation):
    """Delete text at a specific position."""
    length: int
    deleted_text: Optional[str] = None  # Store for undo
    
    def apply(self, document: str) -> str:
        """Delete text from the document."""
        # Store deleted text for undo if not already stored
        if self.deleted_text is None:
            self.deleted_text = document[self.position:self.position + self.length]
        return document[:self.position] + document[self.position + self.length:]
    
    def transform(self, other: Operation, priority: bool = False) -> Operation:
        """Transform this delete against another operation."""
        if isinstance(other, InsertOp):
            if other.position <= self.position:
                # Insert happens before delete, adjust delete position
                return DeleteOp(
                    position=self.position + len(other.text),
                    length=self.length,
                    deleted_text=self.deleted_text,
                    client_id=self.client_id,
                    version=self.version
                )
            elif other.position >= self.position + self.length:
                # Insert happens after delete range, no change
                return self
            else:
                # Insert happens within delete range, extend delete
                return DeleteOp(
                    position=self.position,
                    length=self.length + len(other.text),
                    deleted_text=self.deleted_text,
                    client_id=self.client_id,
                    version=self.version
                )
        
        elif isinstance(other, DeleteOp):
            if other.position + other.length <= self.position:
                # Other delete is before this one
                return DeleteOp(
                    position=self.position - other.length,
                    length=self.length,
                    deleted_text=self.deleted_text,
                    client_id=self.client_id,
                    version=self.version
                )
            elif other.position >= self.position + self.length:
                # Other delete is after this one
                return self
            else:
                # Overlapping deletes
                if other.position <= self.position:
                    # Other starts before or at same position
                    if other.position + other.length >= self.position + self.length:
                        # Other completely covers this delete
                        return DeleteOp(
                            position=other.position,
                            length=0,
                            deleted_text="",
                            client_id=self.client_id,
                            version=self.version
                        )
                    else:
                        # Partial overlap at start
                        overlap = other.position + other.length - self.position
                        return DeleteOp(
                            position=other.position,
                            length=self.length - overlap,
                            deleted_text=self.deleted_text[overlap:] if self.deleted_text else None,
                            client_id=self.client_id,
                            version=self.version
                        )
                else:
                    # Other starts within this delete
                    if other.position + other.length >= self.position + self.length:
                        # Partial overlap at end
                        return DeleteOp(
                            position=self.position,
                            length=other.position - self.position,
                            deleted_text=self.deleted_text[:other.position - self.position] if self.deleted_text else None,
                            client_id=self.client_id,
                            version=self.version
                        )
                    else:
                        # Other is completely within this delete
                        return DeleteOp(
                            position=self.position,
                            length=self.length - other.length,
                            deleted_text=self.deleted_text,
                            client_id=self.client_id,
                            version=self.version
                        )
        
        return self
    
    def invert(self) -> 'InsertOp':
        """Create an insert operation that undoes this delete."""
        if self.deleted_text is None:
            raise ValueError("Cannot invert delete without deleted_text")
        return InsertOp(
            position=self.position,
            text=self.deleted_text,
            client_id=self.client_id,
            version=self.version + 1
        )


class OTEngine:
    """
    Operational Transformation engine for managing concurrent edits.
    
    This engine handles the transformation and application of operations
    to maintain consistency across multiple clients.
    """
    
    def __init__(self):
        self.document: str = ""
        self.version: int = 0
        self.pending_operations: List[Operation] = []
        
    def apply_local(self, operation: Operation) -> Tuple[Operation, str]:
        """
        Apply a local operation and return the transformed operation.
        
        Returns:
            Tuple of (transformed_operation, new_document_text)
        """
        # Apply to local document
        self.document = operation.apply(self.document)
        operation.version = self.version
        self.version += 1
        
        log.debug(f"Applied local operation: {operation}")
        return operation, self.document
    
    def apply_remote(self, operation: Operation) -> str:
        """
        Apply a remote operation after transforming against pending local operations.
        
        Returns:
            The new document text after applying the operation
        """
        # Transform against all pending operations
        transformed_op = operation
        for pending_op in self.pending_operations:
            transformed_op = transformed_op.transform(pending_op, priority=False)
        
        # Apply the transformed operation
        self.document = transformed_op.apply(self.document)
        self.version += 1
        
        log.debug(f"Applied remote operation: {transformed_op}")
        return self.document
    
    def acknowledge_operation(self, operation: Operation):
        """Remove an acknowledged operation from pending queue."""
        self.pending_operations = [
            op for op in self.pending_operations 
            if op.client_id != operation.client_id or op.version != operation.version
        ]
    
    def compose_operations(self, op1: Operation, op2: Operation) -> List[Operation]:
        """
        Compose two operations into a minimal set of operations.
        
        This is useful for reducing network traffic by combining multiple
        operations into fewer operations.
        """
        # Simple implementation - can be optimized
        if isinstance(op1, InsertOp) and isinstance(op2, InsertOp):
            if op1.position + len(op1.text) == op2.position:
                # Adjacent inserts can be combined
                return [InsertOp(
                    position=op1.position,
                    text=op1.text + op2.text,
                    client_id=op1.client_id,
                    version=op1.version
                )]
        
        elif isinstance(op1, DeleteOp) and isinstance(op2, DeleteOp):
            if op1.position == op2.position:
                # Adjacent deletes can be combined
                return [DeleteOp(
                    position=op1.position,
                    length=op1.length + op2.length,
                    deleted_text=(op1.deleted_text or "") + (op2.deleted_text or ""),
                    client_id=op1.client_id,
                    version=op1.version
                )]
        
        # Cannot compose, return both
        return [op1, op2]
    
    def get_state(self) -> dict:
        """Get the current state of the engine."""
        return {
            "document": self.document,
            "version": self.version,
            "pending_operations": len(self.pending_operations)
        }


# WebSocket Integration Interface
class OTWebSocketInterface:
    """
    Interface for integrating OT engine with WebSocket layer.
    
    This provides the methods that Gemini's WebSocket implementation
    will call to handle operations.
    """
    
    def __init__(self):
        self.engines: dict[str, OTEngine] = {}  # document_id -> engine
    
    def get_engine(self, document_id: str) -> OTEngine:
        """Get or create an engine for a document."""
        if document_id not in self.engines:
            self.engines[document_id] = OTEngine()
        return self.engines[document_id]
    
    async def handle_operation(self, document_id: str, operation_data: dict) -> dict:
        """
        Handle an incoming operation from WebSocket.
        
        Args:
            document_id: ID of the document being edited
            operation_data: Dict containing operation details
            
        Returns:
            Dict with transformed operation and new document state
        """
        engine = self.get_engine(document_id)
        
        # Parse operation from data
        op_type = operation_data.get("type")
        if op_type == "insert":
            operation = InsertOp(
                position=operation_data["position"],
                text=operation_data["text"],
                client_id=operation_data["client_id"],
                version=operation_data.get("version", 0)
            )
        elif op_type == "delete":
            operation = DeleteOp(
                position=operation_data["position"],
                length=operation_data["length"],
                client_id=operation_data["client_id"],
                version=operation_data.get("version", 0)
            )
        else:
            raise ValueError(f"Unknown operation type: {op_type}")
        
        # Apply the operation
        if operation_data.get("is_local", False):
            transformed_op, new_text = engine.apply_local(operation)
            return {
                "operation": {
                    "type": op_type,
                    "position": transformed_op.position,
                    "text": getattr(transformed_op, "text", None),
                    "length": getattr(transformed_op, "length", None),
                    "version": transformed_op.version,
                    "client_id": transformed_op.client_id
                },
                "document": new_text,
                "version": engine.version
            }
        else:
            new_text = engine.apply_remote(operation)
            return {
                "document": new_text,
                "version": engine.version
            }