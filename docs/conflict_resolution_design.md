# Conflict Resolution Design for Real-time Collaboration

## Overview

This document outlines the conflict resolution system for Autodoc's real-time documentation collaboration feature. The system ensures multiple developers can work on documentation simultaneously without losing work.

## Architecture Decision: CRDT vs OT

### Operational Transformation (OT) - Recommended
- **Pros**: 
  - Proven in Google Docs, Microsoft Office Online
  - Centralized server makes it easier to implement
  - Better for text editing scenarios
  - Simpler conflict resolution logic
- **Cons**: 
  - Requires central server
  - Complex transformation functions

### CRDT (Conflict-free Replicated Data Types)
- **Pros**: 
  - Works offline/P2P
  - Eventually consistent
  - No central server required
- **Cons**: 
  - More complex for rich text
  - Larger memory footprint
  - Harder to implement undo/redo

**Decision**: Use OT with a central server for initial implementation.

## Conflict Resolution Strategies

### 1. Automatic Resolution
- **Character-level conflicts**: Last-write-wins with operation transformation
- **Line-level conflicts**: Merge if changes are on different lines
- **Section-level conflicts**: Alert users if same section modified

### 2. Conflict Types & Solutions

#### Concurrent Edits
```python
# User A types: "The function returns"
# User B types: "This method outputs"
# Resolution: Show both, highlight conflict
```

#### Delete vs Edit
```python
# User A deletes paragraph
# User B edits same paragraph
# Resolution: Preserve edit, notify about attempted deletion
```

#### Structural Changes
```python
# User A moves section up
# User B adds content to section
# Resolution: Apply move, then add content to new location
```

## Implementation Design

### Core Components

```python
class ConflictResolver:
    def __init__(self):
        self.operation_history = []
        self.active_sessions = {}
    
    def transform_operation(self, op1, op2):
        """Transform op1 against op2"""
        if isinstance(op1, InsertOp) and isinstance(op2, InsertOp):
            if op1.position < op2.position:
                return op1
            elif op1.position > op2.position:
                return InsertOp(op1.position + len(op2.text), op1.text)
            else:
                # Same position - use session priority
                return self._resolve_same_position(op1, op2)

class OperationHistory:
    def __init__(self, max_size=1000):
        self.operations = deque(maxlen=max_size)
        self.checkpoints = {}
    
    def add_operation(self, op):
        self.operations.append(op)
        if len(self.operations) % 100 == 0:
            self.create_checkpoint()
```

### Conflict UI/UX

```typescript
interface ConflictUI {
  // Visual indicators
  highlightConflict(range: Range, users: User[]): void;
  
  // Resolution dialog
  showResolutionDialog(conflict: Conflict): Promise<Resolution>;
  
  // Real-time awareness
  showUserCursors(positions: Map<User, Position>): void;
  showUserSelections(selections: Map<User, Range>): void;
}
```

### Manual Override Interface

```python
class ConflictOverride:
    def __init__(self):
        self.manual_resolutions = {}
    
    def register_override(self, conflict_id, resolution):
        """Allow user to manually resolve a conflict"""
        self.manual_resolutions[conflict_id] = resolution
    
    def apply_override(self, conflict):
        """Apply manual resolution if available"""
        if conflict.id in self.manual_resolutions:
            return self.manual_resolutions[conflict.id]
        return None
```

## Test Scenarios

### 1. Basic Concurrent Edit
- User A: Types "Hello" at position 0
- User B: Types "World" at position 0
- Expected: Both see "HelloWorld" or "WorldHello" (deterministic)

### 2. Overlapping Edits
- User A: Changes "foo" to "bar"
- User B: Changes "foo" to "baz"
- Expected: Conflict dialog appears

### 3. Delete vs Edit Race
- User A: Deletes line 5
- User B: Edits line 5 simultaneously
- Expected: Edit preserved, deletion notification

### 4. Rapid Fire Edits
- Multiple users typing quickly in same area
- Expected: All changes preserved, proper ordering

### 5. Network Partition
- User loses connection mid-edit
- Expected: Local changes preserved, merged on reconnect

## Integration Points

### With WebSocket Layer (Gemini's design)
```python
class ConflictWebSocketHandler:
    async def handle_operation(self, ws, operation):
        # Transform against concurrent operations
        transformed = self.resolver.transform(operation)
        
        # Broadcast to other clients
        await self.broadcast(transformed, exclude=ws)
        
        # Store in history
        self.history.add(transformed)
```

### With History System
```python
class UndoRedoWithConflicts:
    def undo(self, user_id):
        # Find last operation by user
        op = self.history.find_last_by_user(user_id)
        
        # Create inverse operation
        inverse = op.invert()
        
        # Transform against subsequent operations
        transformed = self.transform_to_current(inverse)
        
        # Apply
        self.apply_operation(transformed)
```

## Performance Considerations

1. **Operation Batching**: Group rapid operations to reduce network traffic
2. **Compression**: Use operation compression for similar consecutive edits
3. **Lazy Loading**: Only load conflict resolution UI when needed
4. **Caching**: Cache transformation results for common patterns

## Security Considerations

1. **Operation Validation**: Ensure operations are valid before transformation
2. **Permission Checks**: Verify user has edit rights before applying
3. **Rate Limiting**: Prevent operation spam
4. **Audit Trail**: Log all operations for accountability

## Next Steps

1. Implement core OT algorithm
2. Create conflict visualization UI
3. Build test suite with edge cases
4. Integrate with WebSocket layer
5. Performance testing with multiple concurrent users

---

This design complements Gemini's WebSocket implementation and provides a robust foundation for real-time collaboration in Autodoc.