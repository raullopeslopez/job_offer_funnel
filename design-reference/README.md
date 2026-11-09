# Visual anchors redesign — design reference

Reference implementation of the premium UI (v2) **with visual anchors**: icons, company avatars, two-line rows,
priority bars, stage progress, history timeline, metric tiles, empty states and hover-revealed row actions.

This folder is a **visual reference, not production code**. It is a plain-React + CSS-variables mock of the MUI app.
The real app (`frontend/`) must implement the same result with **MUI components + `theme.ts`**, not by copying these files.

## How to view it
The page loads components with XHR, so it needs a local server (opening the file directly will not work):

```bash
cd design-reference
python3 -m http.server 8000      # or: npx serve .
# open http://localhost:8000/ui_kits/web-premium/index.html
```
Theme toggle (light/dark) is at the bottom of the side nav. Resize under 900px for the mobile shell.

## Where each change lives
| Change | Reference file | Implement in the real app with |
|---|---|---|
| Nav icons | `ui_kits/web-premium/App.jsx` (NAV), `components/navigation/SideNav.jsx` | `ListItemIcon` + `@mui/icons-material/*Outlined` |
| Stage/outcome icons in chips | `components/status/StageChip.jsx` (ICONS map) | `Chip icon={…}` + `toneOf` in `handoff/theme.ts` |
| Company avatar (logo → initial fallback) | `ui_kits/web-premium/ui.jsx` → `CompanyAvatar` | `Avatar variant="rounded"` with `src` + `onError` fallback |
| Two-line rows | `ui.jsx` → `TwoLine`, `Meta`; screens' DataGrid columns | DataGrid `renderCell` + `rowHeight={64}` |
| Relative dates | `ui.jsx` → `RelDate` | small util + `Tooltip` with the full date |
| Priority bars | `ui.jsx` → `PriorityBars` | small component (Box) |
| Stage progress | `ui.jsx` → `StageProgress` | small component (Box), or `LinearProgress` segments |
| History timeline | `ui.jsx` → `Timeline`; `ApplicationDetailScreen.jsx` | `@mui/lab` Timeline or Box/List |
| Field icons in Details | `components/data/FieldList.jsx`; `ApplicationDetailScreen.jsx` | icon next to each label |
| Metric tiles + inline rate bars | `ui.jsx` → `StatTile`; `MetricsScreen.jsx` | `Paper` grid; `LinearProgress variant="determinate"` |
| Keyword tokens | `ui.jsx` → `Token(s)`; `SearchesScreen.jsx` | `Chip size="small"` |
| Tab counts | `ui.jsx` → `TabLabel`; Inbox / Settings | `Tab label={<>… <Chip/></>}` |
| Hover-revealed row actions | `ui_kits/web-premium/index.html` (`.row-actions` CSS), screens | `sx` on DataGrid: `.MuiDataGrid-row:hover .row-actions` + `@media (hover:none)` |
| Empty states | `ui.jsx` → `EmptyState`; `components/data/DataGrid.jsx` | DataGrid `slots={{ noRowsOverlay }}` |
| Theme / tokens | `tokens/premium.css` | `handoff/theme.ts` (already maps 1:1) |

## Icon names
Reference uses the Material Icons Outlined font (`<span class="material-icons-outlined">send</span>`).
In MUI, `send` → `SendOutlined` from `@mui/icons-material`. Same glyphs.

## Notes
- Sample company websites end in `.example`, so the reference always shows the initial fallback. Real domains load favicons
  (`https://www.google.com/s2/favicons?domain={domain}&sz=64`); swap for Logo.dev/Brandfetch if better quality is needed.
- "Today" in the reference is Mar 5, 2026 (to match sample data); the real app uses the current date.
- Copy rules unchanged: English UI, sentence case, raw domain values, "—" for empty.
