import re

WIKI_LINK_RE = re.compile(r'\[\[([^\]]+)\]\]')


def extract_wiki_links(content: str) -> list[str]:
    """Extract [[Title]] links from markdown content, excluding code blocks."""
    # Strip code blocks first
    text = re.sub(r'```[\s\S]*?```', '', content)
    text = re.sub(r'`[^`]+`', '', text)
    return WIKI_LINK_RE.findall(text)


def parse_wiki_link(raw: str) -> dict:
    """Parse a wiki link into its type and target.

    Supports:
    - [[Note Title]] -> type='note', target='Note Title'
    - [[run:uuid]] -> type='run', target='uuid'
    - [[doc:filename]] -> type='doc', target='filename'
    - [[wiki:Concept]] -> type='wiki', target='Concept'
    - [[entity:Name]] -> type='entity', target='Name'
    """
    raw = raw.strip()
    if ':' in raw:
        parts = raw.split(':', 1)
        return {"type": parts[0], "target": parts[1], "raw": raw}
    return {"type": "note", "target": raw, "raw": raw}


def find_backlinks(workspace_id: str, target_title: str, client) -> list[dict]:
    """Find all notes in a workspace that link to a given title."""
    if not isinstance(target_title, str) or not re.match(r'^[a-zA-Z0-9_\-\s\(\)\.\,\!\?\:\/]+$', target_title):
        return []
    try:
        response = client.table("notes").select("id, title, content, updated_at") \
            .eq("workspace_id", workspace_id) \
            .ilike("content", f'%[[{target_title}]]%') \
            .execute()
        return response.data or []
    except Exception:
        return []

