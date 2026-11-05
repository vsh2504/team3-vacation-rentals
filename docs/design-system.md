# StayNest design system

Direction chosen with the Anthropic `frontend-design` skill (installed via
`npx skills add https://github.com/anthropics/skills --skill frontend-design`
into `.agents/skills/frontend-design`, symlinked at `.claude/skills/`).
Tokens live in `frontend/src/design/tokens.css`; pages and components consume
them with `var(--sn-*)`. Feature pages are out of scope for this document.

## Subject and intent
Audience: guests comparing stays, hosts managing listings, admins moderating.
Primary job: make availability, price and location scannable fast. The skill
asks us to avoid templated defaults, so we drop the current red-pink
"Airbnb clone" accent and the cream/terracotta look. StayNest is a harbor-town
stay finder: calm tide teal, ink-blue text, marigold signal color.

## Color
| Token | Hex | Use |
|---|---|---|
| ink | #12272d | body text |
| ink-muted | #4a5f66 | secondary text (6.4:1 on white) |
| surface / soft / sunk | #fff / #f1f5f5 / #e4ecec | page, panels, stripes |
| primary | #0b6169 | buttons, links, focus (white on it 7.1:1) |
| accent | #f2b134 | ratings, "booked today" badge; always ink text |
| success / warning / danger | #1b6a38 / #8a5a00 / #b3261e | status text; each has a `-tint` background |

Status is never color-only: pair with an icon or text ("Available", "Pending").
Control borders use `line-strong` (>=3:1); `line` is decorative only.

## Typography
- Display (page and listing titles, price figures): `--sn-font-display`, a
  serif stack, weight 600, tight leading 1.15. Gives the brand warmth.
- Body/UI: `--sn-font-body`, system sans, 16px base, leading 1.55.
- Scale: 13 / 14 / 16 / 20 / fluid 24-32 / fluid 32-52. Max line length 68ch.
- Sentence case labels; no all-caps eyebrows, no single-word accent in headings.

## Spacing, shape, elevation
- 4px base scale `--sn-space-1..8`. Section gaps 3rem, card gaps 1.5rem.
- Radius by size: controls 6px, cards 10px, search panel/modals 18px, pills 999px.
- Elevation: rest (cards), raised (hover/sticky header), overlay (menus,
  dialogs). Prefer border + soft fill at rest; shadow only for lift.

## Interaction
- Single motion moment: the search results reveal. Other motion answers user
  actions only (expand, confirm), 120-220ms. Reduced motion is honored globally.
- Primary button: teal fill, white text. Secondary: white with strong border.
  Destructive (cancel booking, remove listing): danger outline, confirm step.
- Hover never carries information alone; every hover state has a focus twin.

## Accessibility (req. 8.4)
- Visible focus: global `:focus-visible` 3px teal outline plus white halo,
  works on dark and light backgrounds. Never `outline: none` without a replacement.
- Every input has a `<label>` (or `aria-label`); errors use `role="alert"`,
  non-urgent status (saved, booked) uses `role="status"` / `aria-live="polite"`.
- Field errors are linked with `aria-describedby` and `aria-invalid`.
- Targets are at least 44x44px. Text contrast >=4.5:1, UI/graphics >=3:1.
- Maps (OpenStreetMap) are supplementary: every marker location also appears
  in the list as text; map container has an `aria-label`. Photos need alt text,
  videos controls and no autoplay. Charts need a table or text summary.
- Provide a skip link and landmark roles (`header`, `nav`, `main`).

## Responsive layout (req. 8.2)
Mobile first; breakpoints 600 / 900 / 1200px.
- Nav: wraps or collapses to a menu button below 600px; links stay 44px high.
- Search bar: stacked fields on mobile, single row at >=900px.
- Results: one column (list), then `repeat(auto-fill, minmax(280px,1fr))`;
  >=900px adds a sticky map column beside the list. On mobile a "Map / List"
  toggle swaps them instead of stacking a tiny map.
- Cards: image 4:3 with `object-fit: cover`, text wraps, price never truncates.
- Forms: single column below 600px; labels above inputs.
- Tables (host listings, admin queue, analytics): wrap in a horizontally
  scrollable container (`overflow-x: auto`, focusable with `tabindex="0"` and a
  label) or reflow to stacked rows below 600px.
- Media uses `max-width: 100%`; never fixed pixel widths. Test at 360, 768, 1280.
