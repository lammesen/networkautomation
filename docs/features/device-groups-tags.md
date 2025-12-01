# Device Tags and Groups

Organize devices using flexible tags and reusable groups. Tags are simple labels (with color and optional category). Groups are named sets of devices, either static (manual membership) or dynamic (rule‑based). Use them to target automation, compliance, and reporting.

## Tags
- Each tag belongs to a customer and has name, color, optional category/description [1]
- The UI shows device counts per tag and lets you delete a tag (removes from devices) [1]
- Common categories: environment (production, staging), role, region

Create a tag
1) Devices → Tags → Create New Tag
2) Provide name, color, optional category and description, and customer
3) Save — the tag appears in the table with device counts [1]

## Groups
- Static groups: you manage membership manually [1]
- Dynamic groups: membership is computed by filter rules (e.g., vendor=cisco, role=switch) [1]
- Each group shows device count, description, customer, and type [1]

Create a group
1) Devices → Groups → Create New Group
2) Choose Type: Static or Dynamic
3) Set Customer and Name; optionally add Description
4) For Dynamic, add Filter Rules (vendor, platform, site, role — string matches) [1]
5) Create — the group appears in the table; open the group to see the computed members [1]

Group detail page
- Shows total devices, customer, created date
- For Dynamic groups, displays filter rules
- Members table lists hostname, IP, vendor, platform, site, and enabled status, with a link to the Device page [1]

## Targeting with tags and groups
- Commands: select scope by tag(s) or group(s)
- Compliance: define policy scopes by tag or group
- Config: preview/deploy operations against group/tag scopes

## Sources
1. PR #60 UI templates for Groups/Tags (groups.html, group_detail.html, _groups_table.html, _group_devices.html, tags.html, _tags_table.html)
   https://github.com/lammesen/networkautomation/pull/60
