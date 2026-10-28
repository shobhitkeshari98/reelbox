"""
Reelbox - Web Dashboard API
Serves the Notion-style dashboard and API endpoints for browsing, searching, and syncing saved reels.
"""

import os
import json
import csv
import io
import httpx
from fastapi import FastAPI, Query, Body, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from database import (
    init_db, get_reels_by_user, get_categories_by_user,
    get_reel_count, delete_reel, get_all_users_with_reels,
    update_reel_category, get_reel_by_id, get_user_by_token
)

app = FastAPI(title="Reelbox Dashboard")

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/", response_class=HTMLResponse)
async def home(token: str = Query(None), demo: str = Query(None), vault: str = Query(None)):
    """
    Serve dashboard vault if token or demo/vault param is present.
    Otherwise serve the clean product landing page.
    """
    if token or demo or vault:
        with open(os.path.join(TEMPLATES_DIR, "dashboard.html"), "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    with open(os.path.join(TEMPLATES_DIR, "landing.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/landing", response_class=HTMLResponse)
async def landing():
    """Direct route for the product landing page."""
    with open(os.path.join(TEMPLATES_DIR, "landing.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/vault", response_class=HTMLResponse)
async def vault():
    """Direct route for dashboard vault."""
    with open(os.path.join(TEMPLATES_DIR, "dashboard.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/case-study", response_class=HTMLResponse)
async def case_study():
    """Direct route for Product Design Case Study."""
    with open(os.path.join(TEMPLATES_DIR, "case_study.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/api/demo/reels")
async def api_demo_reels(
    category: str = Query(None),
    platform: str = Query(None),
    search: str = Query(None),
    sort_by: str = Query("newest"),
    limit: int = Query(200, le=500),
    offset: int = Query(0),
):
    """Read-only demo reels showcase for public visitors."""
    users = await get_all_users_with_reels()
    if not users:
        return JSONResponse([])
    demo_user_id = users[0]["user_id"]
    reels = await get_reels_by_user(
        demo_user_id,
        category=category,
        platform=platform,
        search=search,
        sort_by=sort_by,
        limit=limit,
        offset=offset
    )
    return JSONResponse(reels)


@app.get("/api/demo/categories")
async def api_demo_categories():
    """Read-only demo categories for showcase."""
    users = await get_all_users_with_reels()
    if not users:
        return JSONResponse([])
    demo_user_id = users[0]["user_id"]
    cats = await get_categories_by_user(demo_user_id)
    return JSONResponse(cats)


@app.get("/api/demo/stats")
async def api_demo_stats():
    """Read-only demo stats for showcase."""
    users = await get_all_users_with_reels()
    if not users:
        return JSONResponse({"total_reels": 0, "total_categories": 0, "categories": []})
    demo_user_id = users[0]["user_id"]
    count = await get_reel_count(demo_user_id)
    cats = await get_categories_by_user(demo_user_id)
    return JSONResponse({
        "total_reels": count,
        "total_categories": len(cats),
        "categories": cats
    })


@app.get("/api/users")
async def api_users():
    """Get all users with saved reels."""
    users = await get_all_users_with_reels()
    return JSONResponse(users)


@app.get("/api/vault/verify")
async def api_vault_verify(token: str = Query(...)):
    """Verify a private vault token and return user info."""
    user = await get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid vault token")
    return JSONResponse(user)


@app.get("/api/reels/{user_id}")
async def api_reels(
    user_id: int,
    category: str = Query(None),
    platform: str = Query(None),
    search: str = Query(None),
    sort_by: str = Query("newest"),
    limit: int = Query(200, le=500),
    offset: int = Query(0),
):
    """Get reels for a user with global search and filtering."""
    reels = await get_reels_by_user(
        user_id,
        category=category,
        platform=platform,
        search=search,
        sort_by=sort_by,
        limit=limit,
        offset=offset
    )
    return JSONResponse(reels)


@app.get("/api/reels/{user_id}/categories")
async def api_categories(user_id: int):
    """Get categories and counts for a user."""
    cats = await get_categories_by_user(user_id)
    return JSONResponse(cats)


@app.get("/api/thumbnail/{reel_id}")
async def api_thumbnail(reel_id: int):
    """Proxy and stream thumbnail directly from Instagram/YouTube CDN to bypass CORS/hotlinking."""
    reel = await get_reel_by_id(reel_id)
    if not reel or not reel.get("thumbnail_url"):
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    thumb_url = reel["thumbnail_url"].replace("&amp;", "&")
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(
                thumb_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            if resp.status_code == 200:
                content_type = resp.headers.get("content-type", "image/jpeg")
                return Response(
                    content=resp.content,
                    media_type=content_type,
                    headers={"Cache-Control": "public, max-age=86400"}
                )
    except Exception as e:
        print(f"Thumbnail proxy failed for reel #{reel_id}: {e}")
    raise HTTPException(status_code=404, detail="Could not load image")


@app.get("/api/reels/{user_id}/stats")
async def api_stats(user_id: int):
    """Get stats for a user."""
    count = await get_reel_count(user_id)
    cats = await get_categories_by_user(user_id)
    return JSONResponse({
        "total_reels": count,
        "total_categories": len(cats),
        "categories": cats
    })


@app.patch("/api/reels/{user_id}/{reel_id}/category")
async def api_update_category(
    user_id: int,
    reel_id: int,
    payload: dict = Body(...)
):
    """Update a reel's category (for Notion Kanban drag-and-drop)."""
    new_cat = payload.get("category")
    if not new_cat:
        raise HTTPException(status_code=400, detail="Category is required")

    success = await update_reel_category(user_id, reel_id, new_cat)
    if success:
        return JSONResponse({"status": "updated", "category": new_cat})
    return JSONResponse({"status": "not_found"}, status_code=404)


@app.delete("/api/reels/{user_id}/{reel_id}")
async def api_delete_reel(user_id: int, reel_id: int):
    """Delete a reel."""
    deleted = await delete_reel(user_id, reel_id)
    if deleted:
        return JSONResponse({"status": "deleted"})
    return JSONResponse({"status": "not_found"}, status_code=404)


@app.get("/api/reels/{user_id}/export")
async def api_export(user_id: int, format: str = Query("markdown")):
    """
    Export reels in Notion-ready Markdown, CSV, or JSON format.
    """
    reels = await get_reels_by_user(user_id, limit=1000)

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Category", "Subcategory", "Summary", "Key Points", "Tags", "URL", "Platform", "Created At"])
        for r in reels:
            tags = ", ".join(json.loads(r["tags"] or "[]"))
            points = "; ".join(json.loads(r["key_points"] or "[]"))
            writer.writerow([r["id"], r["category"], r["subcategory"], r["summary"], points, tags, r["url"], r["platform"], r["created_at"]])
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=reelbox_export_{user_id}.csv"}
        )

    elif format == "json":
        return JSONResponse(reels)

    else:
        # Default: Notion Markdown Database format
        md_lines = [
            f"# 📦 Reelbox Vault Export\n",
            f"*Exported {len(reels)} categorized bookmarks*\n\n",
            "---\n"
        ]
        
        # Group by category
        grouped = {}
        for r in reels:
            cat = r["category"] or "Uncategorized"
            grouped.setdefault(cat, []).append(r)

        for cat, items in grouped.items():
            md_lines.append(f"## 📂 {cat} ({len(items)})\n")
            for r in items:
                tags = " ".join([f"`#{t}`" for t in json.loads(r["tags"] or "[]")])
                key_points = json.loads(r["key_points"] or "[]")
                
                md_lines.append(f"### [{r['subcategory'] or cat}] {r['summary'][:90]}")
                md_lines.append(f"- **Link:** [{r['platform'].capitalize()}]({r['url']})")
                md_lines.append(f"- **Tags:** {tags}")
                if key_points:
                    md_lines.append("- **Key Takeaways:**")
                    for pt in key_points:
                        md_lines.append(f"  - [ ] {pt}")
                md_lines.append(f"- *Added: {r['created_at']}*\n")

        return Response(
            content="\n".join(md_lines),
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=reelbox_notion_{user_id}.md"}
        )


@app.post("/api/reels/{user_id}/sync-notion")
async def api_sync_notion(
    user_id: int,
    payload: dict = Body(...)
):
    """
    Sync all saved reels directly into an official Notion database!
    Requires:
    - notion_token: 'secret_...' (from notion.so/my-integrations)
    - database_id: '...' (ID of the target Notion database)
    """
    notion_token = payload.get("notion_token")
    database_id = payload.get("database_id", "").replace("-", "")

    if not notion_token or not database_id:
        raise HTTPException(status_code=400, detail="Missing notion_token or database_id")

    reels = await get_reels_by_user(user_id, limit=50)
    synced_count = 0
    errors = []

    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        for r in reels:
            tags = [{"name": t[:50]} for t in json.loads(r["tags"] or "[]")][:5]
            key_points = json.loads(r["key_points"] or "[]")
            
            # Build Notion page blocks for key takeaways
            children_blocks = []
            if key_points:
                children_blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {"rich_text": [{"type": "text", "text": {"content": "💡 Key Takeaways"}}]}
                })
                for pt in key_points:
                    children_blocks.append({
                        "object": "block",
                        "type": "to_do",
                        "to_do": {
                            "rich_text": [{"type": "text", "text": {"content": pt[:2000]}}],
                            "checked": False
                        }
                    })

            page_data = {
                "parent": {"database_id": database_id},
                "properties": {
                    "Name": {
                        "title": [{"text": {"content": (r["summary"] or r["subcategory"] or r["category"])[:100]}}]
                    },
                    "Category": {
                        "select": {"name": r["category"][:50]}
                    },
                    "URL": {
                        "url": r["url"]
                    }
                },
                "children": children_blocks
            }

            try:
                resp = await client.post("https://api.notion.com/v1/pages", json=page_data, headers=headers)
                if resp.status_code in (200, 201):
                    synced_count += 1
                else:
                    errors.append(f"Reel #{r['id']}: {resp.status_code}")
            except Exception as e:
                errors.append(f"Reel #{r['id']}: {str(e)}")

    return JSONResponse({
        "status": "completed",
        "total": len(reels),
        "synced": synced_count,
        "errors": errors[:5]
    })


@app.post("/api/vault/sync")
async def api_vault_sync(data: dict = Body(...), secret_key: str = Query(None)):
    """Import reels & user data from backup or local sync."""
    expected_key = os.getenv("GEMINI_API_KEY")
    if not secret_key or secret_key != expected_key:
        raise HTTPException(status_code=403, detail="Unauthorized")

    users = data.get("users", [])
    reels = data.get("reels", [])
    from database import import_sync_data
    await import_sync_data(users, reels)
    return JSONResponse({"status": "ok", "users_synced": len(users), "reels_synced": len(reels)})


@app.get("/api/vault/export")
async def api_vault_export(secret_key: str = Query(None)):
    """Export all reels & users for backup."""
    expected_key = os.getenv("GEMINI_API_KEY")
    if not secret_key or secret_key != expected_key:
        raise HTTPException(status_code=403, detail="Unauthorized")

    from database import export_sync_data
    data = await export_sync_data()
    return JSONResponse(data)
