import pytest
from pathlib import Path
import tempfile
from autodoc.cli import SimpleAutodoc, SimpleASTAnalyzer


def test_ast_analyzer():
    analyzer = SimpleASTAnalyzer()
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('def test():\n    """Test"""\n    pass')
        temp_path = Path(f.name)
    
    try:
        entities = analyzer.analyze_file(temp_path)
        assert len(entities) == 1
        assert entities[0].name == 'test'
    finally:
        temp_path.unlink()


@pytest.mark.asyncio
async def test_autodoc():
    autodoc = SimpleAutodoc()
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text('def hello():\n    """Hi"""\n    pass')
        
        summary = await autodoc.analyze_directory(Path(tmpdir))
        assert summary['functions'] == 1
