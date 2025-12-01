shadcn/ui quick patterns
========================
- Buttons: `class="inline-flex items-center justify-center gap-2 rounded-md border px-3 py-2 text-sm font-medium transition focus:outline-none focus:ring"`; use variants (primary/destructive/ghost) via existing utilities.
- Cards/Sections: `rounded-lg border bg-card text-card-foreground p-6 space-y-3` for content blocks.
- Tables: `table w-full text-sm` with headers `text-xs uppercase text-muted-foreground`; wrap in `div` with `overflow-x-auto` for responsiveness.
- Forms: stack with `space-y-2`; use `Label` + `Input|Select|Textarea|Switch|Checkbox`; include help text and error text classes.
- Dialog/Sheet: use shadcn Dialog components; close via `DialogClose`; apply `max-h-[80vh] overflow-auto` for content.
- Command palette: use Command/CommandInput/CommandGroup/CommandItem; ensure keyboard shortcuts displayed.
- Layout utilities: `flex items-center gap-2`, `grid gap-4`, `muted` text for secondary info; prefer `text-sm` default.
