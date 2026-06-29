import { motion } from "framer-motion"

const steps = [
  "Searching documents...",
  "Generating answer...",
]

export function LoadingIndicator({ step = 0 }: { step?: number }) {
  return (
    <div className="flex items-start gap-3 px-4 py-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary">
        <div className="h-4 w-4">
          <motion.div
            className="h-full w-full rounded-full border-2 border-foreground border-t-transparent"
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          />
        </div>
      </div>
      <div className="space-y-1.5 pt-1">
        <p className="text-sm text-muted-foreground">
          {steps[step] || "Processing..."}
        </p>
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="h-1.5 w-1.5 rounded-full bg-muted-foreground/40"
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{ duration: 1.2, delay: i * 0.2, repeat: Infinity }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
