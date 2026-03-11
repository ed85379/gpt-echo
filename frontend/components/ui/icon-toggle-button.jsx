// components/ui/icon-toggle-button.jsx
import { cn } from "@/lib/utils"

export function IconToggleButton({ pressed, onClick, title, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      aria-pressed={pressed}
      className={cn(
        "inline-flex h-8 w-8 items-center justify-center rounded-md text-xs",
        "transition-colors transition-transform",
        pressed
          ? [
              "bg-purple-600 text-white",
              // bright top edge, darker bottom edge
              "shadow-[0_-1px_0_rgba(255,255,255,0.7),0_1px_0_rgba(0,0,0,0.9)]",
              "translate-y-[1px]",
            ]
          : [
              "bg-neutral-950 text-neutral-400",
              "border border-neutral-700",
              // lighter bottom edge = raised
              "shadow-[0_1px_0_rgba(255,255,255,0.5)]",
              "hover:bg-neutral-900 hover:text-neutral-100",
            ]
      )}
    >
      {children}
    </button>
  )
}