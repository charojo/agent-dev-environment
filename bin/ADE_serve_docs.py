#!/usr/bin/env python3
## @DOC
# ### Documentation Server
# Provides a simple HTTP server to view generated documentation.
# This resolves issues with browser security policies (CORS) when viewing Doxygen search features via `file://`.
#
# **Usage:**
# `uv run python agent_env/bin/ADE_serve_docs.py`

import http.server
import socketserver
import webbrowser
import os
import sys
import socket
from pathlib import Path

def get_available_port(start_port=8080):
    port = start_port
    while port < start_port + 100:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) != 0:
                return port
        port += 1
    return None

def main():
    # Detect roots
    script_dir = Path(__file__).resolve().parent
    agent_env_root = script_dir.parent
    
    # Check if we have a superproject docs/gen
    project_root = agent_env_root.parent
    docs_gen_dir = project_root / "docs" / "gen"
    
    if not docs_gen_dir.exists():
        # Fallback to local
        docs_gen_dir = agent_env_root / "docs" / "gen"
    
    if not docs_gen_dir.exists():
        print(f"Error ❌: Documentation directory not found at {docs_gen_dir}")
        print("Please run documentation generation first: uv run python agent_env/bin/ADE_document.py --pdf")
        sys.exit(1)

    port = get_available_port()
    if not port:
        print("Error ❌: Could not find an available port.")
        sys.exit(1)

    url = f"http://localhost:{port}"
    
    # Change directory to docs/gen to serve specifically that
    os.chdir(docs_gen_dir)
    
    Handler = http.server.SimpleHTTPRequestHandler
    
    print(f"🚀 Serving documentation at: {url}")
    print(f"📂  Source: {docs_gen_dir}")
    print("Press Ctrl+C to stop the server.")

    # Try to open browser
    try:
        # Check if Doxygen exists. Point to proj_name or any subfolder index.
        doxy_dir = docs_gen_dir / "doxygen"
        target_path = ""
        
        if doxy_dir.exists():
            # Try to find a 'main' index. Priority: src -> AGENT -> any other
            priorities = ["src", "AGENT"]
            # Add any other subdirs
            subs = [d.name for d in doxy_dir.iterdir() if d.is_dir()]
            for p in priorities + subs:
                index_path = doxy_dir / p / "html" / "index.html"
                if index_path.exists():
                    target_path = f"doxygen/{p}/html/index.html"
                    break
        
        if target_path:
            webbrowser.open(f"{url}/{target_path}")
        else:
            webbrowser.open(url)
    except Exception:
        pass

    try:
        with socketserver.TCPServer(("", port), Handler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        sys.exit(0)

if __name__ == "__main__":
    main()
