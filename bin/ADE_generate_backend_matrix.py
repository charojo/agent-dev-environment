# ## @DOC
# ### Ade Generate Backend Matrix
# Generates coverage matrix for backend tests.

import json
import os

# Path to .coverage database
DB_PATH = "logs/.coverage"
OUTPUT_FILE = "logs/backend_matrix.json"


def generate_matrix():
    if not os.path.exists(DB_PATH):
        print(f"Coverage database not found at {DB_PATH}")
        return

    print(f"Processing backend coverage from {DB_PATH}...")

    # RE-STRATEGY: Using raw SQL is fragile across versions.
    # Let's use the coverage API.

    try:
        import coverage
    except ImportError:
        print("coverage module not installed.")
        return

    cov = coverage.Coverage(data_file=DB_PATH)
    cov.load()

    cov_data = cov.get_data()

    # Data structure: { "test_name": { "module": percent } }
    matrix = {}

    # cov_data.measured_contexts() returns list of context names
    for context in cov_data.measured_contexts():
        if not context:
            continue  # Skip empty context

        # We need to scope the data to this context
        # coverage API doesn't make it super easy to ask "what is covered by this context only"
        # cleanly without manipulating internal state or creating a new coverage object with
        # specific data. However, cov.data has methods.

        matrix[context] = {}

        # This part is computationally expensive if loop over all files.
        # Ensure we only check files relevant to src

        for file_path in cov_data.measured_files():
            if "src" not in file_path:
                continue

            # Relative path for readability
            rel_path = os.path.relpath(file_path, os.getcwd())
            if rel_path.startswith(".."):
                continue

            # Get lines executed in this context
            try:
                # measured_lines(file_path, context=context) ? No, that's not the API
                # cov.data.lines(file_path, context=context) ??
                # Actually, cov.data.contexts_by_lineno(file_path) returns { lineno: [contexts] }
                # Inverting this is better?
                pass
            except Exception:
                pass

    # Efficient approach:
    # Iterate over all files, get contexts_by_lineno.
    # Aggregate stats per context.

    for file_path in cov_data.measured_files():
        if "src" not in file_path:
            continue

        rel_path = os.path.relpath(file_path, os.getcwd())

        # Get executable lines (total lines)
        # We need an analysis of the file to know total executable lines.
        # cov.analysis(file_path) returns:
        # (filename, executable_statements, excluded_statements, missing_statements, missing_fmt)
        # But cov.analysis checks general measured data, not context specific.
        # Total executable lines is constant regardless of context.

        try:
            analysis = cov._analyze(file_path)  # Internal API, or use public
            executable_lines = set(analysis.statements)
            total_lines = len(executable_lines)

            if total_lines == 0:
                continue

            contexts_by_lineno = cov_data.contexts_by_lineno(file_path)

            # Map context -> executed lines count for this file
            file_context_counts = {}

            for lineno, contexts in contexts_by_lineno.items():
                if lineno not in executable_lines:
                    continue

                for ctx in contexts:
                    if ctx not in file_context_counts:
                        file_context_counts[ctx] = 0
                    file_context_counts[ctx] += 1

            # Update global stats
            for ctx, count in file_context_counts.items():
                if ctx not in matrix:
                    matrix[ctx] = {}

                percent = (count / total_lines) * 100
                matrix[ctx][rel_path] = round(percent, 2)

        except Exception:
            # print(f"Error analyzing {rel_path}: {e}")
            pass

    # Ensure output dir
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(matrix, f, indent=2)

    print(f"Backend matrix generated at {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_matrix()
