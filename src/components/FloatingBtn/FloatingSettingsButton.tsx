interface FloatingSettingsButtonProps {
  onClick: () => void
}

export function FloatingSettingsButton({ onClick }: FloatingSettingsButtonProps) {
  return (
    <button type="button" className="apl-floating-btn" onClick={onClick} aria-label="Open settings">
      Settings
    </button>
  )
}
