# Statistics

The Statistics tab shows the team's own numbers from the league's game sheets. It measures the team only: the sheets
carry no player, and nothing here is broken down by player.

## Who can see it

Only a signed-in team member. The site is public, so the page is built like the team events (`team_crypto.py`): the
figures are rendered to HTML, sealed with the team password (`TEAM_EVENTS_PASSWORD`), and written into the page as
ciphertext. The public page holds a short locked notice, and the browser decrypts the figures after Team Login
(`page_common.SCHEDULE_JS`, the same script as the event pages). With no team password there is no page and no tab
(`page_common.TEAM_ONLY_PAGES`).

The sheets it draws on are sealed too (see `docs/SEALED_SHEETS.md`). `game_shots.json`, the shots a parent counts by hand, is still a plain file in the repository.

## What it shows and how each figure is made

`generate_stats_html.compute` is pure (sheets and shots in, numbers out) and is what `test_stats.py` checks. Only games
the Eagles played in, with a game sheet, are counted.

| Section | Source |
| --- | --- |
| Record, goals for and against, per game | The sheet's final score. |
| Goals by period | The sheet's score by period. |
| Penalties by period, penalties we take and draw | The sheet's penalties, named with `generate_game_pages.penalty_name`. A penalty "we draw" is one the opponent takes. |
| Penalty minutes | Minutes on the sheet, our penalties only. |
| Power play and penalty kill | Worked out from the penalty clocks, because the sheet does not mark power-play goals. See below. |
| Shots | `game_shots.json`, counted by hand for some games. Shooting is our goals over our shots, saves is one minus their goals over their shots, in those games only. |
| Game flow | Our record in games where we scored first, where they did, and where we led or trailed after the 1st and 2nd. A row appears once such a game exists. |

### Power play and penalty kill

Clock times are turned into seconds into the game (periods are 12 minutes). A chance for a team is a minor or major taken
by the other team. Two penalties of the same length called within 5 seconds of each other, one against each team, cancel,
so neither team is shorthanded. A ten minute misconduct gives no chance. A goal is a power-play goal when it is scored
while an opponent's chance is running; a minor ends at that goal, a major does not. Penalty kill is the chances against
us, less the power-play goals they scored, over the chances against us.

Two limits: four-on-four and other uneven stretches are not modelled, and a goal while both teams are short is counted as
even strength. With a handful of games the percentages move a lot from one game to the next.

## Build

`generate_stats_html.py` runs last in the hourly build, after `agilex_sheets.py`, and `statistics.html` is committed with
the other generated pages.

```bash
TEAM_EVENTS_PASSWORD=<test password> python generate_stats_html.py
python -m unittest test_stats
```

Build it with a throwaway password to try it locally and do not commit that file: the hourly build replaces it with the
page sealed under the real team password.
