#!/usr/bin/env python3
"""
Notion Integration Template — Sync data to/from Notion databases.

Setup:
1. Create integration at notion.so/my-integrations
2. Share your database with the integration
3. Set NOTION_API_KEY env var

Requirements:
    pip install requests
"""

import json
import os
import requests

NOTION_API = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": f"Bearer {os.environ.get('NOTION_API_KEY', '')}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


def query_database(database_id, filter_obj=None, sorts=None):
    """Query a Notion database."""
    body = {}
    if filter_obj:
        body["filter"] = filter_obj
    if sorts:
        body["sorts"] = sorts
    
    resp = requests.post(
        f"{NOTION_API}/databases/{database_id}/query",
        headers=HEADERS, json=body,
    )
    resp.raise_for_status()
    return resp.json()["results"]


def create_page(database_id, properties, children=None):
    """Create a page in a Notion database."""
    body = {
        "parent": {"database_id": database_id},
        "properties": properties,
    }
    if children:
        body["children"] = children
    
    resp = requests.post(f"{NOTION_API}/pages", headers=HEADERS, json=body)
    resp.raise_for_status()
    return resp.json()


def update_page(page_id, properties):
    """Update a Notion page's properties."""
    resp = requests.patch(
        f"{NOTION_API}/pages/{page_id}",
        headers=HEADERS,
        json={"properties": properties},
    )
    resp.raise_for_status()
    return resp.json()


# --- Example usage ---

if __name__ == "__main__":
    DATABASE_ID = "your-database-id-here"
    
    # Query all items
    results = query_database(DATABASE_ID)
    for page in results:
        title = page["properties"]["Name"]["title"][0]["text"]["content"]
        print(f"  • {title}")
    
    # Create a new item
    new_page = create_page(DATABASE_ID, {
        "Name": {"title": [{"text": {"content": "New Item from Script"}}]},
        "Status": {"select": {"name": "Todo"}},
        "Tags": {"multi_select": [{"name": "automated"}]},
    })
    print(f"Created: {new_page['id']}")
