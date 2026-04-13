export default function SkeletonCard() {
  return (
    <div
      className="rounded-xl border p-5 space-y-3"
      style={{ backgroundColor: 'var(--color-card)', borderColor: 'var(--color-border)' }}
    >
      <div className="flex justify-between">
        <div className="space-y-2 flex-1">
          <div
            className="h-4 w-36 rounded skeleton-pulse"
            style={{ backgroundColor: 'var(--color-border)' }}
          />
          <div
            className="h-3 w-48 rounded skeleton-pulse"
            style={{ backgroundColor: 'var(--color-border)' }}
          />
        </div>
        <div className="flex gap-1">
          <div
            className="h-5 w-12 rounded-full skeleton-pulse"
            style={{ backgroundColor: 'var(--color-border)' }}
          />
        </div>
      </div>
      <div className="flex gap-3">
        {[1, 2, 3, 4].map(i => (
          <div
            key={i}
            className="h-3 w-20 rounded skeleton-pulse"
            style={{ backgroundColor: 'var(--color-border)' }}
          />
        ))}
      </div>
      <div className="space-y-2 border-t pt-3" style={{ borderColor: 'var(--color-border)' }}>
        {[1, 2].map(i => (
          <div key={i} className="flex items-center gap-2">
            <div
              className="w-6 h-6 rounded-full skeleton-pulse"
              style={{ backgroundColor: 'var(--color-border)' }}
            />
            <div
              className="h-3 w-28 rounded skeleton-pulse"
              style={{ backgroundColor: 'var(--color-border)' }}
            />
          </div>
        ))}
      </div>
      <div
        className="h-3 w-full rounded skeleton-pulse"
        style={{ backgroundColor: 'var(--color-border)' }}
      />
      <div
        className="h-3 w-3/4 rounded skeleton-pulse"
        style={{ backgroundColor: 'var(--color-border)' }}
      />
    </div>
  );
}
