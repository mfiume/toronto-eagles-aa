# Film review

A signed-in viewer who opens a game's film from the game page gets a full-screen review: the game's goals and penalties in a list
on the left, the video on the right. On a phone the video sits on top and the list scrolls below it.

## What opens it

A plain click on a timeline mark, a row of the game sheet lists, or the "Video review" button. A middle click or a click with a
modifier key still goes to the video in a new tab (those links keep their `href`). A mark or row opens the review at its moment
(`data-t`, the second of the video); the button opens it at the start. A game with a film and no placed moments opens the player alone.

## The header

The first line is the game as the page shows it ("The Attack at Toronto Eagles") with the final score and "Final" beside it; the second,
smaller line is the date, time and arena ("Sunday, October 25 · 12:10 PM · Lambton Arena"). Both ellipsize on a phone rather than wrap.
They come from the sealed package's `info` object (`away`, `home`, `score`, `when`), built by `generate_game_pages.film_info` from the
game's schedule row, so the script needs nothing else. A package without `info` shows the plain "Video review" heading. The dialog's
`aria-label` is "Video review, <away> at <home>". The share button (link icon, tooltip "Copy link", then "Link copied" for about two
seconds) sits beside the close button and has the same size and focus ring.

## Shareable address

The game page's address plus `#review` opens the review at the start of the film; `#review=<kind>-<period>-<clock>`
(`#review=goal-2-10:11`) opens it at that moment, using the moments placed in the sealed package. An unknown key opens at the start.
While the review is open the hash follows the current row (which follows playback and clicks) through `history.replaceState`, so no
history entries are added; closing the review removes it. "Copy link" copies `location.href` (`navigator.clipboard`, falling back to
a hidden textarea and `execCommand('copy')`).

A visitor who opens such a link without the team password in `localStorage` ('eagles-team-password'), or with a wrong one, gets the
site's sign-in box (the same markup and classes as the schedule's, built by `FILM_JS` because game pages carry no log-in box). The
review opens after a correct password, which is then stored as on the schedule. The public page contains nothing about the film. The
schedule's video icon still arrives with `#review`.

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
`url`, `moments`, `api`, `info`) and are opened after sign-in with the team password. The public HTML and the shared script contain no video
host text (the unit test searches for `youtu`). Nothing is requested from the video host until the review is opened: the player
script (`api`, with `enablejsapi` handled by the IFrame Player API) is added to the page then, once, and the player is created with
`rel=0, modestbranding=1, playsinline=1, autoplay=1` and `start=t`. A package without `api` keeps the old behaviour (links open the
video in a new tab).

## Tests

- `python3 test_film_review.py`: public page has no video host or id, sealed package carries `api` and the moments, no fetch before open, player settings.
- `node check_film_review.mjs [screenshot dir]`: puppeteer-core against a generated fixture game page with a made-up video id and a stubbed player script; no real request to the video host. Checks the list, seek, highlight while playing, Esc, focus, scroll lock, logged-out page, and writes screenshots at 1100 and 390 px. puppeteer-core is found in `PUPPETEER_CORE_DIR` or the Film Room checkout's `node_modules`.

Rows of the game sheet that open the film are links with a pointer cursor, a hover underline and the tooltip "Video review"; they carry
no icon. The sheet's Scoring, Penalties and Timeouts lists use columns of at least 250 px (three across from about 870 px wide),
with the row text cut by an ellipsis when it is too long; the logo and the minutes never shrink. At 250 px a name as long as
"Interference with the goalie" is cut.
The browser check writes `sheet_lists_<width>.png` and measures row heights and columns at 1100, 1000, 871, 700 and 390 px
against a fixture game with long penalty names.
