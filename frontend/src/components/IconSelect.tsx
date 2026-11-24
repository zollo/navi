import { ICON_NAMES, ICONS } from "../lib/icons";
import type { IconName } from "../types";

export default function IconSelect({
  value,
  onChange,
  id,
  label = "Icon",
}: {
  value: IconName;
  onChange: (icon: IconName) => void;
  id?: string;
  label?: string;
}) {
  return (
    <select
      id={id}
      aria-label={label}
      className="icon-select"
      value={value}
      onChange={(e) => onChange(e.target.value as IconName)}
    >
      {ICON_NAMES.map((name) => (
        <option key={name} value={name}>
          {ICONS[name].label}
        </option>
      ))}
    </select>
  );
}
