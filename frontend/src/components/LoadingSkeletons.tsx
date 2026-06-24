interface SkeletonProps {
  count?: number
  className?: string
}

export function SkeletonLine({ className = '' }: { className?: string }) {
  return (
    <div className={`h-4 bg-white/[0.05] rounded-lg animate-pulse ${className}`} />
  )
}

export function SkeletonCard({ count = 3 }: SkeletonProps) {
  return (
    <div className="space-y-3 p-4">
      <SkeletonLine className="w-1/3 h-5" />
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonLine key={i} className="w-full" />
      ))}
    </div>
  )
}

export function SkeletonList({ count = 5 }: SkeletonProps) {
  return (
    <div className="space-y-2 p-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 p-2 rounded-xl bg-white/[0.03]">
          <div className="w-8 h-8 rounded-lg bg-white/[0.05] animate-pulse" />
          <div className="flex-1 space-y-1.5">
            <SkeletonLine className="w-3/4 h-3" />
            <SkeletonLine className="w-1/2 h-2.5" />
          </div>
        </div>
      ))}
    </div>
  )
}

export function SkeletonCircle({ size = 40 }: { size?: number }) {
  return (
    <div
      className="rounded-full bg-white/[0.05] animate-pulse"
      style={{ width: size, height: size }}
    />
  )
}
