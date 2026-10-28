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

## Filters

A row of pills at the top of the list's pane (it stays put while the list scrolls): All, Goals, Goals for, Goals against, Penalties, each
with its count. "For" and "against" are relative to the Eagles: each row of the game sheet carries `data-side="us"` or `"them"`
(`generate_game_pages.game_sheet.side_of`, only on a game the Eagles play), and the review reads it. A pill whose count is zero, or
equal to All, is left out, and with no pill besides All the row is hidden. The row is a radio group: arrow keys, Home and End move
the selection, and only the selected pill is a tab stop. On a phone the row scrolls sideways; on a wider screen it wraps.
Filtering only hides rows (`hidden` on the list item). The video is not touched, and the current row is the latest *visible*
event at or before the playing time.

The filter rides in the address: `#review=goal-2-10:11&filter=goals-for`, `#review&filter=penalties`. All is not written. An unknown filter
means All, and the earlier forms of `#review` work as before. The per-event link button copies the moment only.

## Highlights

The Highlights button (play icon) plays the clips of the visible list in order, not the continuous game. Each clip starts at the
event's moment `t` and runs `lead + CLIP_AFTER[kind]` seconds (goal 12, penalty 8 after the play, so 32 and 28 seconds with the
20 s lead-in); it is cut short where the next clip starts when that comes first, and that advance does not seek. `CLIP_AFTER` is a named
constant at the top of `REVIEW_JS`.

Under the player: previous, pause or resume, next, "3 of 11" and Stop. The current row is highlighted and scrolled into view. Previous is
off on the first clip; Next on the last, like the end of the last clip, shows "End of highlights" for about 2.5 s, pauses the video and
returns to normal. Stop leaves the video where it is and plays on.

The player's `getCurrentTime()` is read every 250 ms while highlights play (500 ms otherwise). A clip ends when the time reaches its end.
A viewer pause shows Resume and holds the sequence. A time more than 2 s before the clip's start or 3 s after its end, once the
player has had up to 5 s to reach the clip after our own seek, is a seek by the viewer and leaves highlights. Clicking a row during
highlights continues from that clip. A filter change restarts highlights on the new list. The address is `#review=highlights`
(plus `&filter=`) while they play; opening that address plays highlights from the first clip, after the usual sign-in for a visitor who is
not signed in.

## The countdown to the play

A moment's time on the film is `lead` seconds before the play (Film Room places it 20 s early). The sealed package carries it as
`lead` (`generate_game_pages.DEFAULT_LEAD` = 20 when the entry has none; the page also defaults to 20). Under the player, a slim bar fills
toward the play with "Goal in 12 s" or "Penalty in 8 s" and the team's logo. At the play it reads the row's wording
("Goal 3–1", "Tripping, 2 min") with a short emphasis, stays `COUNTDOWN_AFTER` (4) seconds and then goes quiet. It is computed
from the player's time alone: a clicked row, highlights, a seek, a new row and natural playback all behave the same, and only visible
(filtered) events count. A paused player holds it. A separate polite live region says "Goal in 20 seconds" once when an event
starts counting, not every second; the visual bar is hidden from screen readers.

## Behaviour of the layer

Closes with Esc or the close button. Focus moves in on open and returns to the mark, row or button that opened it. The page behind is
`inert` and its scroll is locked; Tab stays inside. The player is destroyed on close, which stops the video.

## Privacy

The video address, id and the player script address exist only in the sealed film package (`generate_game_pages.film_package`, keys
`url`, `moments`, `api`, `info`, `lead`) and are opened after sign-in with the team password. The public HTML and the shared script contain no video
host text (the unit test searches for `youtu`). Nothing is requested from the video host until the review is opened: the player
script (`api`, with `enablejsapi` handled by the IFrame Player API) is added to the page then, once, and the player is created with
`rel=0, modestbranding=1, playsinline=1, autoplay=1` and `start=t`. A package without `api` keeps the old behaviour (links open the
video in a new tab).

## Tests

- `python3 test_film_review.py`: public page has no video host or id, sealed package carries `api` and the moments, no fetch before open, player settings.
- `node check_film_review.mjs [screenshot dir]`: puppeteer-core against a generated fixture game page with a made-up video id and a stubbed player script; no real request to the video host. Checks the list, seek, highlight while playing, the filters (counts, keyboard, address), highlights (order, seek values, advance at the clip length, pause, previous, next, stop, end, a viewer seek, a filter change, the address forms) and the countdown (values at controlled times), Esc, focus, scroll lock, logged-out page, and writes screenshots at 1100 and 390 px. The stub's `getCurrentTime` returns a time the test sets; its `playVideo` and `pauseVideo` report the state change when `auto` is on. puppeteer-core is found in `PUPPETEER_CORE_DIR` or the Film Room checkout's `node_modules`.

Rows of the game sheet that open the film are links with a pointer cursor, a hover underline and the tooltip "Video review"; they carry
no icon. The sheet's Scoring, Penalties and Timeouts lists use columns of at least 250 px (three across from about 870 px wide),
with the row text cut by an ellipsis when it is too long; the logo and the minutes never shrink. At 250 px a name as long as
"Interference with the goalie" is cut.
The browser check writes `sheet_lists_<width>.png` and measures row heights and columns at 1100, 1000, 871, 700 and 390 px
against a fixture game with long penalty names.

## A link to one event

Each event in the review's list has a link button at its right, shown on hover and focus and always on a touch screen. It copies the
game page's address with `#review=<kind>-<period>-<clock>` for that event, the same form the address bar follows, and its tooltip
reads "Link copied" for a moment.
