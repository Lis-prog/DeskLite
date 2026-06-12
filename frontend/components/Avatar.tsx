interface AvatarProps {
  name: string;
  /** Tailwind size class pair, e.g. "h-8 w-8". Defaults to h-8 w-8. */
  size?: string;
}

/** Deterministic colour from a name so the same user always gets the same hue. */
function pickColour(name: string): string {
  const palette = [
    "bg-blue-100 text-blue-700",
    "bg-violet-100 text-violet-700",
    "bg-emerald-100 text-emerald-700",
    "bg-amber-100 text-amber-700",
    "bg-rose-100 text-rose-700",
    "bg-sky-100 text-sky-700",
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
  }
  return palette[hash % palette.length];
}

function initials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");
}

export function Avatar({ name, size = "h-8 w-8" }: AvatarProps) {
  const colour = pickColour(name);
  return (
    <span
      aria-label={name}
      title={name}
      className={`inline-flex items-center justify-center rounded-full text-xs font-semibold ${size} ${colour}`}
    >
      {initials(name)}
    </span>
  );
}