export function Spinner({ size = 'md', className = '' }) {
  const s = { sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-10 h-10' }[size]
  return (
    <div className={`${s} ${className}`}>
      <div className="w-full h-full rounded-full border-2 border-forge-border border-t-forge-accent animate-spin" />
    </div>
  )
}

export function PageSpinner() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-forge-bg">
      <div className="flex flex-col items-center gap-4">
        <Spinner size="lg" />
        <p className="text-forge-text-3 font-mono text-xs tracking-widest">LOADING</p>
      </div>
    </div>
  )
}
