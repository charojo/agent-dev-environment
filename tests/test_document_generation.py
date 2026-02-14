import shutil
import sys
from pathlib import Path

import pytest

# Add bin directory to path for imports if needed,
# but we will likely run the script via subprocess to fully test CLI behavior.
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
BIN_DIR = PROJECT_ROOT / "bin"
DOCUMENT_SCRIPT = BIN_DIR / "ADE_document.py"


@pytest.fixture
def temp_project(tmp_path):
    """Creates a temporary project structure with documentation blocks."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    src_dir = project_dir / "src"
    src_dir.mkdir()

    # Create a python file with docs
    main_py = src_dir / "main.py"
    main_py.write_text("""
## @DOC
# ### Main Service
# This is the main entry point.
# It does things.
def main():
    pass
    """)

    # Create a README
    readme = project_dir / "README.md"
    readme.write_text("# Test Project")

    return project_dir


def test_document_generation(temp_project, capsys):
    """Verifies that document.py generates specs, PDFs, and Doxygen."""

    if not shutil.which("pandoc"):
        pytest.skip("Pandoc not installed, skipping PDF generation test.")

    if not shutil.which("doxygen"):
        pytest.skip("Doxygen not installed, skipping Doxygen generation test.")

    # Run the document script in the context of the temp project
    # But document.py relies on being in bin/ relative to project...
    # Actually document.py detects project root relative to itself.
    # So we might need to mock some things or trick it.
    #
    # Alternatively, we can import the functions from document.py and test them directly.
    # Let's try importing to avoid path hell with the script location assumption.

    sys.path.append(str(BIN_DIR))
    import ADE_document as document

    # Mock global variables or params if necessary?
    # process_project takes specific paths so it should be fine.

    output_dir = temp_project / "docs" / "gen"
    output_dir.mkdir(parents=True)

    # Run functionality
    document.process_project(temp_project, output_dir, "AGENT", generate_pdf_flag=True)

    # 1. Verify DESIGN_SPEC.md
    spec_md = output_dir / "AGENT_DESIGN_SPEC.md"
    assert spec_md.exists()
    content = spec_md.read_text()
    assert "Main Service" in content
    assert "src/main.py" in content

    # 2. Verify DESIGN_SPEC.pdf
    spec_pdf = output_dir / "AGENT_DESIGN_SPEC.pdf"
    assert spec_pdf.exists()
    assert spec_pdf.stat().st_size > 0

    # 3. Verify Structure Map
    # images dir is hardcoded in document.py to GEN_IMAGES_DIR...
    # We need to monkeypatch GEN_IMAGES_DIR if we want it in our temp dir.
    # Or just check if function ran without error (it would print error).
    # Since we imported the module, we can inspect where it put things or if it failed.
    # But wait, `document.py` defines GEN_IMAGES_DIR at module level.
    # We should stick to what `process_project` passes.
    # process_project calls generate_structure_map(..., GEN_IMAGES_DIR / ...)
    # So it uses the global GEN_IMAGES_DIR which is relative to the REAL project root.
    # This might pollute the real gen folder.

    # Let's monkeypatch constants
    document.GEN_DOCS_DIR = output_dir
    document.GEN_IMAGES_DIR = output_dir / "images"
    document.GEN_IMAGES_DIR.mkdir(exist_ok=True)

    # Re-run structure map part specifically to verify isolation
    document.generate_structure_map(
        temp_project, document.GEN_IMAGES_DIR / "structure.svg", {}
    )
    assert (document.GEN_IMAGES_DIR / "structure.svg").exists()

    # 4. Verify Doxygen
    doxygen_dir = output_dir / "doxygen" / "AGENT"
    assert doxygen_dir.exists()
    assert (doxygen_dir / "html" / "index.html").exists()

    # Verify Doxyfile has our new settings
    doxyfile = doxygen_dir / "Doxyfile"
    doxy_content = doxyfile.read_text()
    assert "HAVE_DOT               = YES" in doxy_content
    assert "UML_LOOK               = YES" in doxy_content
