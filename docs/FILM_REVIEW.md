# Film review

A signed-in viewer who opens a game's film from the game page gets a full-screen review: the game's goals and penalties in a list
on the left, the video on the right. On a phone the video sits on top and the list scrolls below it.

## What opens it

A plain click on a timeline mark, a row of the game sheet lists, or the "Video review" button. A middle click or a click with a
modifier key still goes to the video in a new tab (those links keep their `href`). A mark or row opens the review at its moment
(`data-t`, the second of the video); the button opens it at the start. A game with a film and no placed moments opens the player alone.

## The list

Built from the rows already on the game sheet (`li[data-m]`), so the logo, wording ("Goal 1–2", "Hooking 2 min") and styling are the
sheet's own. Only goals and penalties whose moment has a placed time are listed, in game order (period, then clock counting down).
A row with no placed time is left out. Timeouts open the film at their second but are not listed.

While the video plays, `getCurrentTime()` is read every 500 ms and the latest listed event at or before it is the current row
(`is-now`, `aria-current`). Clicking a row calls `seekTo(t, true)` and `playVideo()` on the existing player and updates the
"Open on YouTube" link to that second. Video quality is not set: the player ignores it.

## Behaviour of the layer

Closes with Esc or the close button. Focus moves in on open and returns to the mark, row or button that opened it. The page behind is
`inert` and its scroll is locked; Tab stays inside. The player is destroyed on close, which stops the video.

## Privacy

The video address, id and the player script address exist only in the sealed film package (`generate_game_pages.film_package`, keys
`url`, `moments`, `api`) and are opened after sign-in with the team password. The public HTML and the shared script contain no video
host text (the unit test searches for `youtu`). Nothing is requested from the video host until the review is opened: the player
script (`api`, with `enablejsapi` handled by the IFrame Player API) is added to the page then, once, and the player is created with
`rel=0, modestbranding=1, playsinline=1, autoplay=1` and `start=t`. A package without `api` keeps the old behaviour (links open the
video in a new tab).

## Tests

- `python3 test_film_review.py`: public page has no video host or id, sealed package carries `api` and the moments, no fetch before open, player settings.
- `node check_film_review.mjs [screenshot dir]`: puppeteer-core against a generated fixture game page with a made-up video id and a stubbed player script; no real request to the video host. Checks the list, seek, highlight while playing, Esc, focus, scroll lock, logged-out page, and writes screenshots at 1100 and 390 px. puppeteer-core is found in `PUPPETEER_CORE_DIR` or the Film Room checkout's `node_modules`.
