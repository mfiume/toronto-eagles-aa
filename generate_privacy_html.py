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

        .privacy .intro {
            font-size: 1.02rem;
            color: var(--ink);
            line-height: 1.6;
            margin: 14px 0 4px;
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

INTRO = (
    "Film Room is a hockey video analysis application for the Toronto Eagles. "
    "It is a tool for coaches, players, and families to review game film for "
    "discussion and self-improvement."
)

SECTIONS = [
    ("Who can see the film",
     "Videos are shared within a single team only. They are not to be shared "
     "externally. Film is for the team's coaches, players, and families, and a "
     "link to a video must not be posted publicly or passed to anyone outside "
     "the team."),
    ("How the film is stored",
     "Game film is uploaded to the team's YouTube channel as unlisted videos. "
     "An unlisted video does not appear in search or on the channel page and "
     "can be opened only with its link. Titles and descriptions give the teams, "
     "the date, the rink, and the score. They do not name players."),
    ("What Film Room asks of YouTube",
     "Film Room asks for access to the team's YouTube channel only to upload "
     "these videos and check their status. It does not read anyone else's "
     "account, and it does not collect information from the people who watch."),
    ("What information it keeps",
     "Game film, the league's published game results, and the notes coaches "
     "make while reviewing film. All of it stays within the team. Film Room "
     "does not use advertising, analytics, or tracking, and it does not sell or "
     "share personal information."),
    ("Removal and questions",
     "A video will be taken down on request. For that, or for any question, "
     'contact the team through the <a href="index.html">team page</a>.'),
]

UPDATED = "Updated October 26, 2026"


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
{page_common.masthead("privacy.html", page_common.division_label(), page_common.season_label())}

        <div class="content">
          <article class="privacy">
            <h1>Privacy</h1>
            <p class="lede">{UPDATED}</p>
            <p class="intro">{INTRO}</p>
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
