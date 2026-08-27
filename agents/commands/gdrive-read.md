# Read a Google Drive file

Read the content of a Google Drive `.gdoc` (or `.gsheet`, `.gslides`) file by opening it in Chrome and exporting it as plain text.

## Steps

1. Read the local stub file to extract the `doc_id`:
   - Use the Read tool on the `.gdoc` file — it contains JSON with a `doc_id` field

2. Make sure a Chrome tab is open and authenticated with Google Drive:
   - Use `mcp__claude-in-chrome__tabs_context_mcp` to get available tabs
   - If no tab exists, create one with `mcp__claude-in-chrome__tabs_create_mcp` and navigate to `https://drive.google.com`

3. Fetch the doc content using the in-page fetch trick:
   ```js
   (async () => {
     const docId = 'DOC_ID_HERE';
     const resp = await fetch(`https://docs.google.com/document/d/${docId}/export?format=txt`);
     const text = await resp.text();
     window.__gdoc_text = text;
     return text.slice(0, 5000);
   })()
   ```
   - For Google Sheets, use `format=csv` instead of `format=txt`
   - For Google Slides, use `format=txt`

4. If the content was truncated, fetch more from `window.__gdoc_text`:
   ```js
   window.__gdoc_text.slice(5000, 10000)
   ```

## Notes

- This works because the fetch runs inside the authenticated Chrome session — no API keys needed
- The tab must be on a `*.google.com` page for the auth cookies to apply
- `.gdoc` stubs are ~1KB JSON files — they cannot be read or edited directly, only the `doc_id` matters
