# Tooltips

One tooltip serves the whole site. It is in `page_common.SCHEDULE_JS` and styled by `.tip` in `page_common.py`. Anything with a
`data-tip` attribute gets it. Do not use the browser's `title` attribute for anything a person is meant to read: it is slow,
unstyled, and does not work on a phone.

## Behaviour

- Appears after a short pause on hover, at once on keyboard focus, and on tap. A second tap closes it. It closes on scroll.
- Sits above the element, below it when there is no room above, and stays inside the screen.
- Listens on the document, so content swapped in later (the team version of the schedule) works with no extra code.
- A link opens when tapped; it does not toggle a tooltip.

## Content

- **One line for a plain control or icon**: a verb and its object. "Watch on YouTube", "Watch on LiveBarn", "Win".
- **Several lines for an event**, written as `heading || detail || detail`. The first line is the heading in the display face.
  A goal reads "Goal, Mississauga Jets / 1st period, 11:45 left / Score: Eagles 0, Jets 1".
- Say what the thing is or does, not where the data came from, who may see it, or how to use it.
- No parentheses, no trailing full stop, no "click" or "tap", no "team only", no explanation of the icon next to its label.
- Same words as the visible label when there is one. Title case is not used; the heading is set in capitals by the style.
- Team names are shortened to the nickname in a score line: "Eagles 4, Terriers 9".
- Never a player's name or jersey number.

## Accessibility

- A link or button already has its own accessible name (`aria-label`); the tooltip repeats it for sighted users.
- A mark that is not a link or button and carries a tooltip gets `tabindex="0"` and an `aria-label` with the same words, so a
  keyboard can reach it.

## Marks that open the film

On a game page, a signed-in viewer can open the film at a goal, penalty or timeout. The marks on the game sheet timeline and the rows
in its lists carry `data-m="kind|period|clock"`. When the sealed film package is opened (`FILM_JS` in `page_common.py`), each mark or
row whose moment is placed on the film becomes a link to the video at that second, in a new tab. Moments with no placed time stay as
they were. The tooltip gains a last line, "Watch on YouTube", and a row gets the red play button at its right edge.

The moments come from Film Room in the `GAME_VIDEOS` secret: a game's value is an address alone, or
`{"url", "moments": [{"kind", "period", "clock", "t"}]}`, where `t` is the second of the YouTube video. The package is sealed with the
team password like the film button, so neither the address nor a time is in the public page.
