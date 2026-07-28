#!/usr/bin/env python3
"""
Server to provide JSON files from HTTPS server for ChatGPT and MCP integration.

This server fetches JSON files from a remote HTTPS server and provides them
through a local HTTP interface with useful endpoints.

Usage:
    python server.py --url <remote_url> --port 5000
    python server.py --url https://example.com/path/ --port 8000 -v
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen
from urllib.parse import urljoin, urlparse

try:
    from flask import Flask, jsonify, request
except ImportError:
    print("❌ Error: Flask is required. Install it with: pip install flask")
    sys.exit(1)


class JSONFileCache:
    """Cache for JSON files from remote HTTPS server."""
    
    def __init__(self, base_url: str, verbose: bool = False):
        """Initialize cache."""
        self.base_url = base_url.rstrip("/") + "/"
        self.cache: dict[str, Any] = {}
        self.verbose = verbose
        self.file_index: list[str] = []
        
        if verbose:
            print(f"📌 Cache initialized with base URL: {self.base_url}")
    
    def load_file(self, filename: str) -> dict[str, Any] | None:
        """Load a JSON file from remote server."""
        if filename in self.cache:
            if self.verbose:
                print(f"📦 Loading from cache: {filename}")
            return self.cache[filename]
        
        url = urljoin(self.base_url, filename)
        
        try:
            if self.verbose:
                print(f"📥 Fetching: {url}")
            
            with urlopen(url) as response:
                data = json.loads(response.read().decode("utf-8"))
                self.cache[filename] = data
                
                if self.verbose:
                    print(f"✅ Successfully loaded: {filename}")
                
                return data
        
        except URLError as e:
            print(f"❌ Error fetching {filename}: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ Error decoding JSON from {filename}: {e}")
            return None
    
    def get_file_list(self) -> list[str]:
        """Get list of available JSON files from server.
        
        This attempts to fetch an index or directory listing.
        Returns cached file names if already fetched.
        """
        if self.file_index:
            return self.file_index
        
        # Try to load from a common index file
        for index_name in ["index.json", "files.json", "_index.json"]:
            try:
                index_url = urljoin(self.base_url, index_name)
                with urlopen(index_url) as response:
                    index_data = json.loads(response.read().decode("utf-8"))
                    
                    # Handle different index formats
                    if isinstance(index_data, list):
                        self.file_index = index_data
                    elif isinstance(index_data, dict) and "files" in index_data:
                        self.file_index = index_data["files"]
                    
                    if self.verbose and self.file_index:
                        print(f"✅ Loaded file index: {index_name}")
                    
                    return self.file_index
            except (URLError, json.JSONDecodeError):
                continue
        
        # If no index found, return cached files
        return list(self.cache.keys())


def create_app(cache: JSONFileCache) -> Flask:
    """Create Flask application."""
    app = Flask(__name__)
    
    @app.route("/", methods=["GET"])
    def index() -> dict[str, Any]:
        """API index with available endpoints."""
        return {
            "service": "QE2MCP JSON Server",
            "endpoints": {
                "/": "This help message",
                "/files": "List all available JSON files",
                "/files/<filename>": "Get a specific JSON file",
                "/all": "Get all JSON files combined",
                "/stats": "Get statistics about cached files",
            },
            "usage": "Use /files/<filename> to fetch JSON files from remote HTTPS server",
        }
    
    @app.route("/files", methods=["GET"])
    def list_files() -> dict[str, Any]:
        """List all available JSON files."""
        files = cache.get_file_list()
        return {
            "count": len(files),
            "files": sorted(files),
        }
    
    @app.route("/files/<filename>", methods=["GET"])
    def get_file(filename: str) -> dict[str, Any] | tuple[dict[str, Any], int]:
        """Get a specific JSON file."""
        # Security: prevent directory traversal
        if ".." in filename or filename.startswith("/"):
            return {"error": "Invalid filename"}, 400
        
        data = cache.load_file(filename)
        
        if data is None:
            return {"error": f"File not found: {filename}"}, 404
        
        return {
            "filename": filename,
            "data": data,
            "cached": filename in cache.cache,
        }
    
    @app.route("/all", methods=["GET"])
    def get_all() -> dict[str, Any]:
        """Get all JSON files combined."""
        files = cache.get_file_list()
        all_data = {}
        
        if cache.verbose:
            print(f"📦 Loading {len(files)} files...")
        
        for filename in files:
            data = cache.load_file(filename)
            if data is not None:
                all_data[filename] = data
        
        return {
            "total_files": len(all_data),
            "files": all_data,
        }
    
    @app.route("/stats", methods=["GET"])
    def stats() -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "cached_files": len(cache.cache),
            "cached_filenames": list(cache.cache.keys()),
            "base_url": cache.base_url,
        }
    
    @app.route("/health", methods=["GET"])
    def health() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok"}
    
    return app


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Serve JSON files from HTTPS server for ChatGPT integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python server.py --url https://example.com/jsonfiles/\n"
            "  python server.py --url https://example.com/jsonfiles/ --port 8000\n"
            "  python server.py --url https://example.com/jsonfiles/ -v\n"
        ),
    )
    
    parser.add_argument(
        "--url",
        type=str,
        default="https://ip-163-220-177-91.compute.mdx1.jp/fDpyK7TbE5C1oj1ObA2H/msg3/",
        help="Base URL of HTTPS server with JSON files",
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to run server on (default: 5000)",
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1, use 0.0.0.0 for all interfaces)",
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run in debug mode",
    )
    
    args = parser.parse_args()
    
    # Validate URL
    try:
        parsed = urlparse(args.url)
        if not parsed.scheme.startswith("http"):
            print(f"❌ Error: Invalid URL scheme. Must be http or https: {args.url}")
            return 1
    except Exception as e:
        print(f"❌ Error: Invalid URL: {e}")
        return 1
    
    # Create cache and app
    cache = JSONFileCache(args.url, verbose=args.verbose)
    app = create_app(cache)
    
    # Print startup info
    print(f"🚀 Starting QE2MCP JSON Server")
    print(f"  - URL: {args.url}")
    print(f"  - Server: http://{args.host}:{args.port}")
    print(f"  - Endpoints:")
    print(f"    • http://{args.host}:{args.port}/ - API index")
    print(f"    • http://{args.host}:{args.port}/files - List files")
    print(f"    • http://{args.host}:{args.port}/files/<name> - Get file")
    print(f"    • http://{args.host}:{args.port}/all - Get all files")
    print(f"    • http://{args.host}:{args.port}/health - Health check")
    print()
    
    try:
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            use_reloader=False,
        )
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped")
        return 0
    except Exception as e:
        print(f"❌ Error: Server failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
