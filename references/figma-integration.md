# Figma Integration

## Input formats
- Figma share URL: `https://www.figma.com/file/{key}/...` or `https://www.figma.com/design/{key}/...`
- Figma file key directly
- Exported design screenshots (fallback)

## Parsing

Use `web_fetch` with Figma API or public share link to extract:
- Page/frame structure
- Component tree (buttons, forms, tables, nav, dialogs)
- User flow connections (page-to-page navigation in prototypes)

## Case generation from Figma

Three types:

### Presence cases
For each component found in Figma, check if it exists in the page snapshot:
- Found in both → generate interaction case (verify it works)
- In Figma but missing in page → regression case (component absent)
- In page but not in Figma → note as possible unplanned feature

### Interaction cases
For each interactive component in Figma that also exists in page:
- Generate click/type/select case matching the component's intended behavior

### Flow cases
If Figma has prototype links between frames:
- Generate sequential flow case following the designed user path
- Steps: navigate start → perform each interaction → verify destination

## Three-source merge

Priority: user-specified > figma-generated > ai-exploration

Deduplication: same target_text + same action in different sources → keep highest priority only
Figma presence cases are NOT duplicated by AI exploration cases for the same elements

## Fallback

If Figma fetch fails or returns inaccessible:
- Warn user, proceed with AI exploration + user cases only
- Do not block the test run
