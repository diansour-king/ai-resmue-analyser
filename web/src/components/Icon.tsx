/**
 * Material Symbols Outlined, the icon set the Stitch designs are drawn with. The font is
 * loaded once in the root layout; this component is just the span with the right class and
 * the ligature name as its text.
 */
export function Icon({
  name,
  className = "",
  filled = false,
  "aria-hidden": ariaHidden = true,
}: {
  name: string;
  className?: string;
  filled?: boolean;
  "aria-hidden"?: boolean;
}) {
  return (
    <span
      aria-hidden={ariaHidden}
      className={`material-symbols-outlined select-none${filled ? " fill" : ""} ${className}`}
    >
      {name}
    </span>
  );
}
