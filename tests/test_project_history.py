import sys
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

# Add bin to path
sys.path.append(str(Path(__file__).parent.parent / "bin"))
import ADE_project_history as history_script


def test_analyze_content():
    content = """
    def foo():
        # TODO: Implement this
        pass
        
    def bar():
        # FIXME: Broken
        return 1
    """
    loc, todos, fixmes = history_script.analyze_content(content)
    assert loc == 6
    assert todos == 1
    assert fixmes == 1


def test_is_test_file():
    assert history_script.is_test_file("tests/test_foo.py")
    assert history_script.is_test_file("src/foo.test.js")
    assert history_script.is_test_file("src/components/MyComponent.spec.tsx")
    assert not history_script.is_test_file("src/app.py")


@patch("subprocess.run")
def test_get_commits(mock_run):
    mock_run.return_value = MagicMock(
        stdout="hash1|2024-01-01|Author 1|Subject 1\nhash2|2024-01-02|Author 2|Subject 2",
        returncode=0,
    )

    commits = history_script.get_commits(Path("."), limit=2)
    assert len(commits) == 2
    assert commits[0]["hash"] == "hash1"


@patch("subprocess.run")
def test_get_commits_since(mock_run):
    mock_run.return_value = MagicMock(stdout="hashNew|2024-01-03|Author 3|Subject 3", returncode=0)
    history_script.get_commits(Path("."), since_commit="hash1")
    # Verify git call includes hash1..HEAD
    args = mock_run.call_args[0][0]
    assert "hash1..HEAD" in args


@patch("subprocess.run")
def test_get_files_at_commit(mock_run):
    mock_run.return_value = MagicMock(stdout="file1.py\nfile2.js", returncode=0)
    files = history_script.get_files_at_commit(Path("."), "hash1")
    assert len(files) == 2


def test_parse_existing_history():
    content = """# Header
| Date | Commit | ...
|---|---|...
| 2024-01-02 | `hashNew` | ...
| 2024-01-01 | `hashOld` | ...
"""
    with patch("builtins.open", mock_open(read_data=content)):
        with patch("os.path.exists", return_value=True):
            last = history_script.parse_existing_history("dummy.md")
            assert last == "hashNew"


@patch("ADE_project_history.count_lines_file")
@patch("os.walk")
def test_run_local_analysis(mock_walk, mock_count):
    # Mock file system
    mock_walk.return_value = [(str(Path(".")), [], ["file1.py", "file2.txt"])]
    mock_count.return_value = (10, 1, 0)  # 10 LOC, 1 TODO

    # Mock args
    args = MagicMock()
    args.analyze_local = True
    args.markdown = False
    args.dual = False

    # Capture stdout
    from io import StringIO

    captured_output = StringIO()

    with patch("sys.stdout", new=captured_output):
        # We need to ensure config loading doesn't crash or provides defaults
        # The script handles missing config gracefully
        history_script.run_local_analysis(Path("."), args)

    output = captured_output.getvalue()
    assert "Metric" in output
    assert "Python" in output
    # file1.py should be counted (1 file, 10 LOC)
    # file2.txt ignored (default config)
    assert "1" in output  # Files
