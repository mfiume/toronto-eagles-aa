# Share cards

A link to any public page shows a large card in iMessage, Slack, email and social apps: the page's title, one line under it, and a 1200 x 630 picture.

- The tags come from `page_common.share_tags(card, title, description, page)`. Every generator that writes a public page calls it right after `<title>`. The team event pages are private and carry none.
- The pictures are `assets/share/<card>.png`, one per kind of page (`site`, `schedule`, `standings`, `playoffs`, `statistics`, `game`, `team`). Draw them again with `node make_share_cards.mjs` after changing the look or the words, and commit the PNGs.
- A game page's line is the result once the game is final, otherwise the day, time and rink (`generate_game_pages.share_line`).
- Addresses must be absolute, so `config.SITE_URL` names where the site lives. Change it with the address.
- Checked by `test_share_cards.py`: every card is 1200 x 630, the tags carry absolute addresses, and quotes in a name cannot break a tag.
- Apps keep a card for a while. After changing a picture, ask the app to refresh (Slack: paste the link again after a day; Facebook's Sharing Debugger).
