export function Empty({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      {Icon && (
        <div className="w-14 h-14 rounded-2xl bg-forge-muted/50 flex items-center justify-center mb-4">
          <Icon size={24} className="text-forge-text-3" />
        </div>
      )}
      <h3 className="font-display font-semibold text-forge-text mb-1">{title}</h3>
      {description && <p className="text-forge-text-3 text-sm mb-5 max-w-xs">{description}</p>}
      {action}
    </div>
  )
}
