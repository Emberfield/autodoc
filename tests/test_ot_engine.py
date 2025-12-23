#!/usr/bin/env python3
"""
Test suite for the Operational Transformation engine.

Tests cover all the edge cases and scenarios described in the conflict
resolution design document.
"""

import pytest

from autodoc.ot_engine import DeleteOp, InsertOp, OTEngine, OTWebSocketInterface


class TestBasicOperations:
    """Test basic operation functionality."""

    def test_insert_operation(self):
        """Test basic insert operation."""
        doc = "Hello World"
        op = InsertOp(position=5, text=" Beautiful", client_id="client1", version=0)
        result = op.apply(doc)
        assert result == "Hello Beautiful World"

    def test_delete_operation(self):
        """Test basic delete operation."""
        doc = "Hello Beautiful World"
        op = DeleteOp(position=5, length=10, client_id="client1", version=0)
        result = op.apply(doc)
        assert result == "Hello World"
        assert op.deleted_text == " Beautiful"

    def test_insert_invert(self):
        """Test insert operation inversion."""
        op = InsertOp(position=5, text=" Beautiful", client_id="client1", version=0)
        inverse = op.invert()

        assert isinstance(inverse, DeleteOp)
        assert inverse.position == 5
        assert inverse.length == 10

    def test_delete_invert(self):
        """Test delete operation inversion."""
        doc = "Hello Beautiful World"
        op = DeleteOp(position=5, length=10, client_id="client1", version=0)
        op.apply(doc)  # This sets deleted_text

        inverse = op.invert()
        assert isinstance(inverse, InsertOp)
        assert inverse.position == 5
        assert inverse.text == " Beautiful"


class TestInsertTransformations:
    """Test insert-insert transformations."""

    def test_insert_before_insert(self):
        """Insert A happens before insert B."""
        op_a = InsertOp(position=0, text="Hello ", client_id="A", version=0)
        op_b = InsertOp(position=5, text="World", client_id="B", version=0)

        transformed = op_a.transform(op_b)
        assert transformed.position == 0  # No change

    def test_insert_after_insert(self):
        """Insert A happens after insert B."""
        op_a = InsertOp(position=10, text="!", client_id="A", version=0)
        op_b = InsertOp(position=5, text="World", client_id="B", version=0)

        transformed = op_a.transform(op_b)
        assert transformed.position == 15  # Adjusted by length of B

    def test_insert_same_position_with_priority(self):
        """Two inserts at same position with priority."""
        op_a = InsertOp(position=5, text="AAA", client_id="A", version=0)
        op_b = InsertOp(position=5, text="BBB", client_id="B", version=0)

        # A has priority
        transformed = op_a.transform(op_b, priority=True)
        assert transformed.position == 5

        # A doesn't have priority
        transformed = op_a.transform(op_b, priority=False)
        assert transformed.position == 8  # After B's text


class TestDeleteTransformations:
    """Test delete-delete transformations."""

    def test_delete_before_delete(self):
        """Delete A happens before delete B."""
        op_a = DeleteOp(position=0, length=5, client_id="A", version=0)
        op_b = DeleteOp(position=10, length=5, client_id="B", version=0)

        transformed = op_b.transform(op_a)
        assert transformed.position == 5  # Adjusted for A's deletion

    def test_delete_after_delete(self):
        """Delete A happens after delete B."""
        op_a = DeleteOp(position=10, length=5, client_id="A", version=0)
        op_b = DeleteOp(position=0, length=5, client_id="B", version=0)

        transformed = op_a.transform(op_b)
        assert transformed.position == 5  # Adjusted for B's deletion

    def test_overlapping_deletes_start(self):
        """Delete B overlaps start of delete A."""
        op_a = DeleteOp(position=5, length=10, client_id="A", version=0)
        op_b = DeleteOp(position=0, length=8, client_id="B", version=0)

        transformed = op_a.transform(op_b)
        assert transformed.position == 0
        assert transformed.length == 7  # Reduced by overlap

    def test_overlapping_deletes_complete(self):
        """Delete B completely covers delete A."""
        op_a = DeleteOp(position=5, length=5, client_id="A", version=0)
        op_b = DeleteOp(position=0, length=15, client_id="B", version=0)

        transformed = op_a.transform(op_b)
        assert transformed.length == 0  # Nothing left to delete

    def test_overlapping_deletes_within(self):
        """Delete B is within delete A."""
        op_a = DeleteOp(position=0, length=15, client_id="A", version=0)
        op_b = DeleteOp(position=5, length=5, client_id="B", version=0)

        transformed = op_a.transform(op_b)
        assert transformed.position == 0
        assert transformed.length == 10  # Reduced by B's deletion


class TestMixedTransformations:
    """Test insert-delete transformations."""

    def test_insert_before_delete(self):
        """Insert happens before delete range."""
        insert_op = InsertOp(position=0, text="Hello ", client_id="A", version=0)
        delete_op = DeleteOp(position=10, length=5, client_id="B", version=0)

        transformed = insert_op.transform(delete_op)
        assert transformed.position == 0  # No change

    def test_insert_after_delete(self):
        """Insert happens after delete range."""
        insert_op = InsertOp(position=15, text="World", client_id="A", version=0)
        delete_op = DeleteOp(position=5, length=5, client_id="B", version=0)

        transformed = insert_op.transform(delete_op)
        assert transformed.position == 10  # Adjusted for deletion

    def test_insert_within_delete(self):
        """Insert happens within delete range."""
        insert_op = InsertOp(position=7, text="XXX", client_id="A", version=0)
        delete_op = DeleteOp(position=5, length=5, client_id="B", version=0)

        transformed = insert_op.transform(delete_op)
        assert transformed.position == 5  # Moved to delete start

    def test_delete_spanning_insert(self):
        """Delete range includes insert position."""
        delete_op = DeleteOp(position=5, length=10, client_id="A", version=0)
        insert_op = InsertOp(position=3, text="Hello", client_id="B", version=0)

        transformed = delete_op.transform(insert_op)
        assert transformed.position == 10  # Adjusted for insert
        assert transformed.length == 10  # Length unchanged

    def test_delete_after_insert(self):
        """Delete happens after insert."""
        delete_op = DeleteOp(position=10, length=5, client_id="A", version=0)
        insert_op = InsertOp(position=5, text="Hello", client_id="B", version=0)

        transformed = delete_op.transform(insert_op)
        assert transformed.position == 15  # Adjusted for insert


class TestOTEngine:
    """Test the OT engine functionality."""

    def test_apply_local_operation(self):
        """Test applying a local operation."""
        engine = OTEngine()
        engine.document = "Hello World"

        op = InsertOp(position=5, text=" Beautiful", client_id="client1", version=0)
        transformed_op, new_doc = engine.apply_local(op)

        assert new_doc == "Hello Beautiful World"
        assert engine.version == 1
        assert transformed_op.version == 0

    def test_apply_remote_operation(self):
        """Test applying a remote operation."""
        engine = OTEngine()
        engine.document = "Hello World"

        op = InsertOp(position=5, text=" Beautiful", client_id="client2", version=0)
        new_doc = engine.apply_remote(op)

        assert new_doc == "Hello Beautiful World"
        assert engine.version == 1

    def test_concurrent_operations(self):
        """Test handling concurrent operations."""
        engine = OTEngine()
        engine.document = "Hello"

        # Local operation
        local_op = InsertOp(position=5, text=" World", client_id="local", version=0)
        engine.pending_operations.append(local_op)
        engine.document = local_op.apply(engine.document)

        # Remote operation at same original position
        remote_op = InsertOp(position=5, text=" Beautiful", client_id="remote", version=0)
        new_doc = engine.apply_remote(remote_op)

        # Remote op should be transformed to position 11 (after " World")
        assert new_doc == "Hello World Beautiful"

    def test_operation_composition(self):
        """Test composing adjacent operations."""
        engine = OTEngine()

        # Adjacent inserts
        op1 = InsertOp(position=0, text="Hello", client_id="A", version=0)
        op2 = InsertOp(position=5, text=" World", client_id="A", version=1)

        composed = engine.compose_operations(op1, op2)
        assert len(composed) == 1
        assert composed[0].text == "Hello World"

        # Adjacent deletes
        op3 = DeleteOp(position=0, length=5, deleted_text="Hello", client_id="A", version=2)
        op4 = DeleteOp(position=0, length=6, deleted_text=" World", client_id="A", version=3)

        composed = engine.compose_operations(op3, op4)
        assert len(composed) == 1
        assert composed[0].length == 11


class TestWebSocketInterface:
    """Test the WebSocket integration interface."""

    @pytest.mark.asyncio
    async def test_handle_insert_operation(self):
        """Test handling insert operation from WebSocket."""
        interface = OTWebSocketInterface()

        # Local insert operation
        result = await interface.handle_operation(
            "doc1",
            {
                "type": "insert",
                "position": 0,
                "text": "Hello",
                "client_id": "client1",
                "is_local": True,
            },
        )

        assert result["document"] == "Hello"
        assert result["version"] == 1
        assert result["operation"]["text"] == "Hello"

    @pytest.mark.asyncio
    async def test_handle_delete_operation(self):
        """Test handling delete operation from WebSocket."""
        interface = OTWebSocketInterface()
        engine = interface.get_engine("doc1")
        engine.document = "Hello World"

        # Remote delete operation
        result = await interface.handle_operation(
            "doc1",
            {
                "type": "delete",
                "position": 5,
                "length": 6,
                "client_id": "client2",
                "is_local": False,
            },
        )

        assert result["document"] == "Hello"
        assert result["version"] == 1

    @pytest.mark.asyncio
    async def test_multiple_document_engines(self):
        """Test managing multiple document engines."""
        interface = OTWebSocketInterface()

        # Operations on different documents
        await interface.handle_operation(
            "doc1",
            {
                "type": "insert",
                "position": 0,
                "text": "Doc1",
                "client_id": "client1",
                "is_local": True,
            },
        )

        await interface.handle_operation(
            "doc2",
            {
                "type": "insert",
                "position": 0,
                "text": "Doc2",
                "client_id": "client1",
                "is_local": True,
            },
        )

        assert interface.get_engine("doc1").document == "Doc1"
        assert interface.get_engine("doc2").document == "Doc2"


class TestComplexScenarios:
    """Test complex real-world scenarios from the design doc."""

    def test_rapid_fire_edits(self):
        """Test multiple users typing quickly in same area."""
        engine = OTEngine()
        engine.document = "The quick brown fox"

        # Simulate rapid edits from two users
        # "The quick brown fox" - insert "very " at position 4 (before "quick")
        ops = [
            InsertOp(
                position=4, text="very ", client_id="A", version=0
            ),  # "The very quick brown fox"
            InsertOp(
                position=10, text="fast ", client_id="B", version=0
            ),  # Original pos, needs transform
            DeleteOp(position=19, length=3, client_id="A", version=1),  # Delete "fox"
            InsertOp(position=19, text="dog", client_id="B", version=1),  # Replace with "dog"
        ]

        # Apply first op
        engine.document = ops[0].apply(engine.document)
        assert engine.document == "The very quick brown fox"

        # Transform and apply second op
        op2_transformed = ops[1].transform(ops[0])
        assert op2_transformed.position == 15  # Adjusted for "very " (5 chars)
        engine.document = op2_transformed.apply(engine.document)
        assert engine.document == "The very quick fast brown fox"

        # Continue with remaining ops...

    def test_delete_vs_edit_race(self):
        """Test when one user deletes while another edits."""
        engine = OTEngine()
        engine.document = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"

        # User A deletes Line 3 (positions 14-21)
        delete_op = DeleteOp(position=14, length=7, client_id="A", version=0)

        # User B edits Line 3 at same time
        edit_op = InsertOp(position=18, text=" edited", client_id="B", version=0)

        # Apply delete first
        engine.document = delete_op.apply(engine.document)

        # Transform edit against delete
        transformed_edit = edit_op.transform(delete_op)
        assert transformed_edit.position == 14  # Moved to delete position

        # The edit is preserved at the deletion point
        engine.document = transformed_edit.apply(engine.document)
        assert "edited" in engine.document
