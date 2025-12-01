import { useEffect, useRef, useState } from "react";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";

export type FormSelectOption = { value: string; label: string };

export type FormSelectProps = {
  name: string;
  value?: string;
  placeholder?: string;
  options: FormSelectOption[];
  submitOnChange?: boolean;
  formId?: string;
};

export function FormSelect({ name, value = "", placeholder = "Select", options = [], submitOnChange = false, formId }: FormSelectProps) {
  const [selected, setSelected] = useState<string>(value);
  const hiddenRef = useRef<HTMLInputElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Filter out options with empty values (Radix Select doesn't allow them)
  const validOptions = (options || []).filter(opt => opt.value !== "");

  useEffect(() => {
    if (!containerRef.current) return;
    let hidden = containerRef.current.querySelector<HTMLInputElement>(`input[type="hidden"][name="${name}"]`);
    if (!hidden) {
      hidden = document.createElement("input");
      hidden.type = "hidden";
      hidden.name = name;
      containerRef.current.appendChild(hidden);
    }
    hidden.value = selected === "__clear__" ? "" : selected;
    hiddenRef.current = hidden;
  }, [name, selected]);

  const triggerSubmit = () => {
    if (!submitOnChange) return;
    const form = formId
      ? document.getElementById(formId) as HTMLFormElement | null
      : (containerRef.current?.closest("form") as HTMLFormElement | null);
    form?.requestSubmit();
  };

  const handleValueChange = (val: string) => {
    if (val === "__clear__") {
      setSelected("");
    } else {
      setSelected(val);
    }
    triggerSubmit();
  };

  return (
    <div ref={containerRef} className="w-full">
      <Select value={selected} onValueChange={handleValueChange}>
        <SelectTrigger className="w-full">
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          {/* Add a "clear" option if there's a selection */}
          {selected && (
            <SelectItem value="__clear__">
              <span className="text-muted-foreground">Clear selection</span>
            </SelectItem>
          )}
          {validOptions.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
          {validOptions.length === 0 && !selected && (
            <div className="py-2 px-2 text-sm text-muted-foreground">No options available</div>
          )}
        </SelectContent>
      </Select>
    </div>
  );
}

export default FormSelect;
