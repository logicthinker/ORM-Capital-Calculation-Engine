#!/usr/bin/env python3
"""
Script to generate and export OpenAPI specification
"""

import json
import yaml
import asyncio
from pathlib import Path

from orm_calculator.api import create_app


async def generate_openapi_spec():
    """Generate OpenAPI specification and save to files"""
    
    # Create FastAPI app
    app = create_app()
    
    # Get OpenAPI schema
    openapi_schema = app.openapi()
    
    # Create docs directory if it doesn't exist
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)
    
    # Save as JSON
    json_path = docs_dir / "openapi.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
    
    print(f"OpenAPI JSON specification saved to: {json_path}")
    
    # Save as YAML
    yaml_path = docs_dir / "openapi.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(openapi_schema, f, default_flow_style=False, allow_unicode=True)
    
    print(f"OpenAPI YAML specification saved to: {yaml_path}")
    
    # Generate API documentation summary
    endpoints = []
    for path, methods in openapi_schema.get("paths", {}).items():
        for method, details in methods.items():
            endpoints.append({
                "path": path,
                "method": method.upper(),
                "summary": details.get("summary", ""),
                "tags": details.get("tags", [])
            })
    
    # Save endpoint summary
    summary_path = docs_dir / "api-endpoints.md"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("# API Endpoints Summary\n\n")
        f.write("This document provides a summary of all available API endpoints.\n\n")
        
        # Group by tags
        by_tags = {}
        for endpoint in endpoints:
            for tag in endpoint["tags"] or ["untagged"]:
                if tag not in by_tags:
                    by_tags[tag] = []
                by_tags[tag].append(endpoint)
        
        for tag, tag_endpoints in by_tags.items():
            f.write(f"## {tag.title()}\n\n")
            for endpoint in tag_endpoints:
                f.write(f"- **{endpoint['method']}** `{endpoint['path']}` - {endpoint['summary']}\n")
            f.write("\n")
    
    print(f"API endpoints summary saved to: {summary_path}")
    
    return openapi_schema


if __name__ == "__main__":
    asyncio.run(generate_openapi_spec())