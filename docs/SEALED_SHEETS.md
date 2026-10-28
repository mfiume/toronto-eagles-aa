# Sealed game sheets

The repository and the site are public, so the league's game sheets (goals, penalties, timeouts and the score by period,
with no player named) are not published in the clear. They are sealed with the team password, the same way the team events
are (`team_crypto.py`), and opened in the browser after Team Login.

## At rest: `game_sheets.sealed.json`

`sheet_store.py` reads and writes the sheets. The file in the repository is ciphertext. The hourly build opens it with
`TEAM_EVENTS_PASSWORD`, `agilex_sheets.py` brings it up to date from the league, and it is sealed again only when
something is new (a new seal writes a new file each time). The plain sheets exist only in the build's memory.

- A file left from before sealing, `game_sheets.json`, is read once, sealed, and removed. It is also in `.gitignore`.
- If the team password changes, the sealed file no longer opens. That is not an error: the sheets are fetched again from the
  league, which is where they came from, and sealed under the new password.
- With no password nothing is read or written, and no sheet is shown anywhere.

## On a game page

The public page holds a locked notice where the sheet was (`SHEET_LOCKED`, marked `data-sheet-slot`) and no sheet markup. The
sheet is rendered to HTML at build time and sealed into the same package as the video review (`#game-film`), so one login
opens both. `FILM_JS` puts the sheet in place first and then links its marks and rows to the video, so the review, the links
into the film and the countdown work as before. A game with a sheet and no film seals the sheet alone. A game with no sheet
has no notice.

`test_film_review.py` checks what the public page does and does not carry, and `check_film_review.mjs` drives the sealed
pages in Chrome (it needs Node 22.12 or newer, or `node --experimental-require-module`).

## What this does not cover

- Earlier commits still hold the plain sheets. Removing them means rewriting the repository's history, which this change does
  not do.
- `game_shots.json` is still a plain file.
