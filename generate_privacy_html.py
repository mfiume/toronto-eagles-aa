#!/usr/bin/env python3
"""
Generate the privacy page for Film Room, the team's video tool.

It is built from the same masthead, fonts and styles as every other page, so it
reads as part of the site. The text is short and at a high level on purpose.
"""

import config
import page_common

PRIVACY_CSS = """
        .privacy {
            max-width: 720px;
            margin: 0 auto;
            background: var(--surface);
            border: 1px solid var(--line);
            position: relative;
            overflow: hidden;
            padding: clamp(22px, 5vw, 34px) clamp(18px, 5vw, 32px) clamp(10px, 3vw, 18px);
        }

        .privacy::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: var(--crest);
        }

        .privacy h1 {
            font-family: var(--display);
            font-weight: 600;
            font-size: clamp(1.4rem, 5vw, 1.9rem);
            letter-spacing: 0.045em;
            text-transform: uppercase;
            margin-bottom: 4px;
        }

        .privacy .lede {
            font-size: 0.87rem;
            color: var(--ink-3);
            margin-bottom: 8px;
        }

        .privacy h2 {
            font-family: var(--display);
            font-weight: 600;
            font-size: clamp(0.9rem, 3vw, 1rem);
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: var(--brand);
            margin: clamp(18px, 4vw, 26px) 0 6px;
        }

        .privacy p {
            font-size: 0.95rem;
            color: var(--ink-2);
            line-height: 1.65;
            margin-bottom: 10px;
        }

        .privacy a {
            color: var(--brand);
        }
"""

SECTIONS = [
    ("What it is",
     "Film Room is a personal tool used by one person to review hockey games. "
     "It is not offered to the public and has no sign-up."),
    ("What it does with YouTube",
     "It uploads the owner's own game videos to the owner's own YouTube channel, "
     "and reads back the status of those videos. It does not access anyone "
     "else's account or channel."),
    ("What it collects",
     "Nothing from visitors or other users. It does not use cookies, advertising "
     "or analytics, and it does not sell or share information with anyone."),
    ("Who can see the videos",
     "The owner chooses who can watch each video. Videos are shared only by link "
     "with the team's families."),
    ("Questions",
     'Contact the team through the <a href="index.html">team page</a>.'),
]


def generate_html():
    body = "".join(f"            <h2>{h}</h2>\n            <p>{p}</p>\n" for h, p in SECTIONS)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.SITE_TITLE} - Privacy</title>
{page_common.FONT_LINK}
{page_common.FAVICON_LINKS}
    <style>
{page_common.PAGE_CSS}{PRIVACY_CSS}    </style>
</head>
<body>
    <div class="container">
{page_common.masthead("privacy.html", "Film Room", "Privacy")}

        <div class="content">
          <article class="privacy">
            <h1>Privacy</h1>
            <p class="lede">Film Room, a personal tool for {config.TEAM_NAME} {config.DIVISION}</p>
{body}          </article>
        </div>

{page_common.page_end()}    </div>
</body>
</html>
"""
    with open("privacy.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("HTML page generated: privacy.html")


if __name__ == "__main__":
    generate_html()
