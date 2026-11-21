---
name: "ad-platform-playbook"
description: "Know how every ad platform works in 2026 (Meta, TikTok, Google Search/PMax/Demand Gen, YouTube, Reddit, LinkedIn, Telegram, X, Snapchat, Pinterest, Yandex), recommend a platform mix by market, goal and budget, and check video/image assets against placement specs."
---

# Ad Platform Playbook

**Style rule:** never use em dashes or en dashes in anything you write (replies, specs, captions, files). Use a comma, colon, period, parentheses or a plain hyphen instead.

Each platform has its own buyer mindset, targeting logic, minimums and creative grammar. You choose where the money goes and make sure assets fit before upload.

Reply in the user's language.

## 1. Setup
The script ships with this skill as `scripts/platforms.py` (Python 3; ffprobe for video, Pillow for images). Copy it next to the project first: `mkdir -p tools && cp <this skill>/scripts/platforms.py tools/`.
- `list`, `card meta|tiktok|google|youtube|reddit|linkedin|telegram|x|snapchat|pinterest|yandex`
- `mix --market AZ --goal leads --budget-usd 900 [--b2b] [--young] [--category "real estate"]`
- `specs file1.mp4 file2.jpg --placement meta_reels|meta_feed|meta_stories|tiktok|youtube_shorts|youtube_instream|reddit_feed|linkedin_feed|pinterest|snapchat`

## 2. Platform notes (2026)
- **Meta:** the core in AZ and TR; Advantage+ default; creative diversification; click to WhatsApp; instant forms with CRM feedback.
- **TikTok:** Smart+ automation, Spark Ads; daily minimum over 50 USD per campaign and over 20 USD per ad group; conversion campaigns realistically 100 to 250 USD/day per ad group; creative wears out fast.
- **Google:** Search with AI Max captures existing demand; Performance Max across inventory; Demand Gen is now full-funnel on YouTube, Discover, Gmail and Maps; add negatives.
- **YouTube:** biggest share of social traffic in AZ, about 40% of internet traffic in TR; Shorts 9:16, in-stream skippable after 5 seconds.
- **Reddit:** community, interest and keyword targeting (keywords in feed and conversations); write like a member; small in AZ and TR.
- **LinkedIn:** B2B only; about 10 USD/day minimum; expensive clicks.
- **Telegram Ads:** contextual (channels, topics, language), 160 characters plus a button; TON/Gram cabinet promotes Telegram links only; EUR cabinet via agencies allows external links.
- **X, Snapchat, Pinterest, Yandex:** niche roles (news and sports in TR; Gulf youth; planning categories; Russian speakers).

## 3. Workflow
1. Run `mix` with the real budget; under about 500 USD a month concentrate on one platform.
2. Give the platform card(s) to the user and adapt the strategy from **ad-strategy-architect** to each platform's objectives.
3. Before upload, run `specs` on every asset and fix ratio, resolution, duration, missing audio and safe zones.
4. Compare platforms monthly by cost per qualified result in your own CRM, not by each platform's self-reported ROAS.
