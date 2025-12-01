# Configuration Templates (Jinja2)

Create reusable configuration templates with variables and platform tags, then render previews with sample inputs. Templates help standardize configuration generation and support multiple vendors/platforms.

## Capabilities
- Per‑customer templates with name, category, status (active/inactive), description [1]
- Jinja2 template content editor with variables schema (JSON) [1]
- Platform tags (JSON array) to label vendor/platform applicability [1]
- Preview rendering: provide values for defined variables and render output [2]
- List page with search and category filter; detail page with metadata and variables doc [3]

## UI
- Templates → List: browse templates, filter by category, open a template to edit [3]
- Templates → New: create a new template using the form [4]
- Template → Detail: edit fields and content, review variables, render preview with inputs [2]

## Variables Schema
Define variables in JSON to document and guide input collection during preview.

Example:
```json
{
  "hostname": {"type": "string", "required": true, "description": "Device hostname"},
  "asn": {"type": "integer", "required": true},
  "loopback_ip": {"type": "string", "required": false, "default": "10.0.0.1"}
}
```

During preview, the UI shows an input for each variable with the default value if present, and renders the Jinja2 template using those values.

## Sources
1. Template form UI: templates/_form.html in PR #60
2. Render result UI: templates/_render_result.html in PR #60
3. List table UI: templates/_table.html and templates/list.html in PR #60
4. Create/detail pages: templates/create.html and templates/detail.html in PR #60
   https://github.com/lammesen/networkautomation/pull/60
