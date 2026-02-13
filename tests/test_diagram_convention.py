import pytest
from pathlib import Path
import subprocess
import shutil
import sys

# Add bin to path to import sanitize_name if needed
BIN_DIR = Path(__file__).resolve().parent.parent / "bin"
sys.path.append(str(BIN_DIR))

@pytest.fixture
def temp_project(tmp_path):
    """Setup a temporary project with a markdown file and mermaid blocks."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    
    docs_dir = project_dir / "docs"
    docs_dir.mkdir()
    
    assets_dir = docs_dir / "assets" / "diagrams"
    assets_dir.mkdir(parents=True)
    
    # Create a markdown file with two mermaid blocks
    md_file = project_dir / "test_doc.md"
    md_file.write_text("""
# Test Document

Here is a diagram with a caption comment.

<!-- caption: Sequence Flow -->
```mermaid
sequenceDiagram
    Alice->>Bob: Hello
```

And another one with YAML frontmatter.

```mermaid
---
title: State Machine
---
stateDiagram-v2
    [*] --> Still
    Still --> [*]
```

And a raw one with no caption.

```mermaid
graph TD
    A --> B
```
""")
    
    # Create a dot file
    dot_file = project_dir / "structure.dot"
    dot_file.write_text('digraph G { label="System Architecture"; A -> B; }')

    return project_dir

def test_diagram_convention(temp_project):
    """Verify that ADE_generate_diagrams.py follows the new convention."""
    
    # Run the script
    script_path = BIN_DIR / "ADE_generate_diagrams.py"
    
    # First run: should compile mermaid but NOT structure.dot (since it's not referenced)
    subprocess.run([sys.executable, str(script_path), str(temp_project)], check=True)
    
    diagrams_dir = temp_project / "docs" / "assets" / "diagrams"
    assert (diagrams_dir / "test_doc_1_sequence_flow.mmd").exists()
    assert (diagrams_dir / "test_doc_2_state_machine.mmd").exists()
    assert (diagrams_dir / "test_doc_3_diagram.mmd").exists()
    
    # DOT file should NOT be compiled yet because it's not in the MD
    assert not (diagrams_dir / "structure_1_system_architecture.svg").exists()

    # Second run: Add a reference to the dot file in MD
    md_file = temp_project / "test_doc.md"
    content = md_file.read_text()
    # Add a figure reference to the dot file
    content += "\n\nfigure 4: System Layout\n\n"
    content += "![figure 4: System Layout](docs/assets/diagrams/test_doc_4_system_layout.svg)\n"
    content += "[figure 4: System Layout source](structure.dot)\n"
    md_file.write_text(content)
    
    subprocess.run([sys.executable, str(script_path), str(temp_project)], check=True)
    
    # Now it should be compiled as a figure of test_doc
    assert (diagrams_dir / "test_doc_4_system_layout.svg").exists()
    assert (diagrams_dir / "test_doc_4_system_layout.dot").exists()

    # Third run: Test cleanup
    # Create a rogue file
    rogue_file = diagrams_dir / "rogue_diagram.svg"
    rogue_file.write_text("<svg></svg>")
    
    assert rogue_file.exists()
    
    subprocess.run([sys.executable, str(script_path), str(temp_project)], check=True)
    
    # Cleanup should have deleted it
    assert not rogue_file.exists()

    # Check Markdown content consistency
    md_content = md_file.read_text()
    assert "figure 1: Sequence Flow" in md_content
    assert "figure 4: System Layout" in md_content
    assert "![figure 4: System Layout](docs/assets/diagrams/test_doc_4_system_layout.svg)" in md_content

if __name__ == "__main__":
    # If run directly, just test it
    pytest.main([__file__])
