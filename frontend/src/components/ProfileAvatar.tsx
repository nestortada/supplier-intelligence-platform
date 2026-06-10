import { User } from 'lucide-react'
import { cx } from '../utils/classNames'

type ProfileAvatarProps = {
  avatarDataUrl?: string | null
  name: string
  className?: string
  imageClassName?: string
}

function profileInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (!parts.length) {
    return 'U'
  }
  return parts.slice(0, 2).map((part) => part[0]?.toUpperCase()).join('')
}

export default function ProfileAvatar({ avatarDataUrl, className, imageClassName, name }: ProfileAvatarProps) {
  return (
    <div
      className={cx(
        'flex shrink-0 items-center justify-center overflow-hidden rounded-full border border-primary/25 bg-gradient-to-br from-primary/25 to-success/10 text-sm font-bold text-primary',
        className,
      )}
    >
      {avatarDataUrl ? (
        <img alt={name} className={cx('h-full w-full object-cover', imageClassName)} src={avatarDataUrl} />
      ) : name.trim() ? (
        <span>{profileInitials(name)}</span>
      ) : (
        <User className="h-5 w-5" />
      )}
    </div>
  )
}
