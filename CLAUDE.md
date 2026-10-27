# Production application

Film Room and the Toronto Eagles team site are production applications that real families and coaches use. Everything on screen is product copy and is held to that standard.

- Write what a finished product would say: short, plain, specific labels and sentences. No placeholder wording, no apologies, no hedging, no exclamation marks.
- Keep the build out of the copy. Where a number came from, who typed it in, what is approximate, what is not built yet, and how a feature works internally belong in docs or code comments. They go on screen only when the person needs them to make a decision.
- Do not explain how to use the interface in the interface.
- No internal jargon and no invented terms. Use the words coaches and parents already use (shots, goals, penalties, period, game sheet).
- Before shipping any new text, ask whether a polished sports product would say it. If not, cut it or reword it.
- This applies to labels, headings, empty states, tooltips, errors, titles and descriptions sent to YouTube, and the privacy page.
- Never use em dashes.

## Tooltips and interface details

The full rules are in docs/TOOLTIPS.md. In short:

- Use the site's single tooltip (a `data-tip` attribute), never the browser's `title`.
- One line for a control or icon: a verb and its object ("Watch on YouTube"). Several lines for an event, heading first.
- No "(team only)", no source notes, no instructions, no parentheses, no trailing full stop.
- Any new interface element is built to the standard of the existing ones before it ships: consistent spacing, alignment with its
  neighbours, light and dark, phone width, keyboard focus. Check it in a screenshot at desktop and phone width and look at it.
- Document a new shared behaviour in docs/ in the same change.
