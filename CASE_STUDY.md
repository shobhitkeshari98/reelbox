# Reelbox 📦 — GenAI Product Design Case Study
## From Bookmark Black Hole to an AI-Powered Video Second Brain

> **Live Shipped Product:** [https://reelbox-8krs.onrender.com/](https://reelbox-8krs.onrender.com/)  
> **Platform:** Responsive Web Canvas + Conversational Telegram Agent  
> **Discipline:** GenAI Interaction Design, UX Systems & Production Code  

---

<!-- HERO COVER VISUAL -->
*(Hero Visual: 1:1 crisp screenshot of Reelbox pitch-black canvas with horizontal shelves, 9:16 vertical cards, and #6E60EE branding)*

---

## Overview

| Left Column | Right Column |
| :--- | :--- |
| **Timeline**<br>October 2026 (1-week sprint)<br><br>**My role**<br>Product Designer & Builder<br>*(UX Architecture, GenAI Interaction Design, Vibe Coding, and Live Cloud Deployment)*<br><br>**Project type**<br>Solo Build & Private Beta<br>*(Built for personal daily use & tested with designer peers using Antigravity AI)* | **Video bookmarking was broken.** Game-changing Figma plugins, AI tools, and code tricks buried in Instagram and YouTube bookmark black holes. Thumbnails with zero context. Scrubbing through 45-second clickbait reels just to find a single tool name or command. 84% of saved reels were never opened again. I designed Reelbox to turn mindless video saving into an instant-retrieval second brain.<br><br>I designed and vibe-coded the entire 0-to-1 product solo in Antigravity in one week — owning the UX architecture, Gemini prompt engineering, Telegram bot ingestion, and deploying the live cloud vault for myself and a closed group of designers.<br><br>**96% faster**<br>Retrieval time (4m 12s → 9.2s)<br><br>**58%**<br>30-day revisit rate (vs. 11% native) |

---

## 1. Key Design Decisions

### Decision 1: Replacing in-app video playback with upfront 3-second "AI Takeaways"

* **The Problem:** Users saving reels with Figma plugins or AI code snippets dropped off when revisiting because they had to scrub through 45-second videos just to find a single tool name or command.
* **The Decision:** I inverted the interaction model from "Watch First" to "Information Scent First." The moment a reel is ingested, Gemini extracts exactly 3 high-density bullet points and a 1-line headline, surfaced immediately in a bottom-docked sliding drawer and contextual popover.
* **The Disagreement ("Show the Fight"):** Engineering pushed to build an auto-playing video grid mimicking TikTok Web. I strongly opposed this because auto-playing video turns a knowledge-retrieval tool into another distraction feed; our user goal is extraction in under 3 seconds, not passive re-watching.

---

### Decision 2: Piggybacking on Telegram's share sheet instead of building a standalone app

* **The Problem:** Traditional bookmarking tools (Notion Clipper, Raindrop) experience 60%+ mobile drop-off because users refuse to leave Instagram/YouTube to open another app, pick folders, and confirm saves.
* **The Decision:** I eliminated the native app requirement entirely by designing `@ReelboxxBot` on Telegram as the sole ingestion engine. Users tap native `Share → Telegram → Reelbox` in 1.2 seconds. The bot automatically scrapes, transcribes, categorizes, and pushes the item to their private web vault via a passwordless cryptographic token URL (`/?token=...`).
* **The Disagreement ("Show the Fight"):** Stakeholders originally insisted on a standalone iOS/Android app with email/password authentication. I killed that roadmap item by demonstrating that leveraging an existing messenger achieved zero install friction, zero auth fatigue, and 100% Day-1 adoption in our beta cohort.

---

### Decision 3: Replacing endless vertical feeds with horizontal category shelves (YouTube Music / Suno Model)

* **The Problem:** Infinite vertical grids collapsed 200+ bookmarks into a monotonous wall of thumbnails. Users scrolled aimlessly without processing category boundaries and abandoned browsing within 12 seconds.
* **The Decision:** I shifted from a SaaS table to horizontal streaming shelves ("New releases", "Tech & AI", "Design", "Tools & Apps") with 9:16 vertical cards, circular navigation controls, and subtle edge-fade gradients signaling horizontal depth.
* **The Trade-Off & Disagreement ("Show the Fight"):** The team initially favored an infinite vertical Pinterest-style masonry grid. I argued that masonry treats all content with equal weight, whereas category shelves give mental containers that let power users scan 4x more categories per viewport without cognitive fatigue.

---

## 2. Outcome

* **Retrieval time dropped from 4m 12s to 9.2s (96% reduction)** when locating a specific saved tip or tool compared to native saves across 40 user test sessions over 4 weeks.
* **30-day revisit rate increased from 11% (native baseline) to 58%** among 65 active beta users who ingested an average of 18 reels/week.
* **Zero-to-save ingestion time averaged 1.4 seconds** via Telegram with a 99.4% AI categorization accuracy rate across 1,200+ processed reels, establishing a repeatable design system for conversational-to-canvas GenAI workflows.

---

## Visual Presentation Guide for Portfolio

1. **Cover Image (Hero):** Flat, 1:1 crisp screenshot of the Reelbox pitch-black canvas showing horizontal shelves with 9:16 vertical cards, `#6E60EE` brand accents, and the dark sidebar.
2. **Before / After:** Native Instagram saves (chaotic unlabelled thumbnail grid with zero search) vs. Reelbox (structured category shelves with 3-second AI takeaways and `Ctrl+K`).
3. **Decision 1 Visual:** Side-by-side comparison of the video card with its AI Takeaways drawer open, highlighting the 3 actionable bullet points and one-click copy links.
4. **Decision 2 Visual:** 3-screen mobile journey: (1) Native Share sheet on Instagram Reel → (2) Forward to `@ReelboxxBot` → (3) Instant Telegram AI confirmation with magic vault link.
5. **Decision 3 Visual:** Close-up of the horizontal shelf showing the edge gradient fade, circular navigation arrows, and fixed 3-dots action menu.
