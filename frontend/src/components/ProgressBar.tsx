type ProgressBarProps = {
  value: number
  tone?: 'primary' | 'success' | 'warning' | 'danger'
}

const toneClass: Record<NonNullable<ProgressBarProps['tone']>, string> = {
  primary: 'bg-primary',
  success: 'bg-success',
  warning: 'bg-warning',
  danger: 'bg-danger',
}

export default function ProgressBar({ value, tone = 'primary' }: ProgressBarProps) {
  const safeValue = Math.max(0, Math.min(value, 100))

  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-panelHigh">
      <div
        className={`${toneClass[tone]} h-full rounded-full transition-all duration-500`}
        style={{ width: `${safeValue}%` }}
      />
    </div>
  )
}
