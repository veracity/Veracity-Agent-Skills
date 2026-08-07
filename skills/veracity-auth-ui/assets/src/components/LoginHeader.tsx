import { CurrentUser } from '../api/auth'

interface LoginHeaderProps {
  projectName: string
  loading: boolean
  isAuthenticated: boolean
  user: CurrentUser | null
  onSignIn: () => void
  onSignOut: () => void
}

// Minimal login-state header: a Sign in button when signed out, or the user's
// name + Sign out when signed in. No UI framework — plain elements keep deps light.
export default function LoginHeader({
  projectName,
  loading,
  isAuthenticated,
  user,
  onSignIn,
  onSignOut
}: LoginHeaderProps) {
  return (
    <header
      style={{
        alignItems: 'center',
        borderBottom: '1px solid #e5e7eb',
        display: 'flex',
        justifyContent: 'space-between',
        padding: '12px 24px'
      }}
    >
      <strong>{projectName}</strong>
      <div>
        {loading ? (
          <span aria-label="Loading sign-in status">…</span>
        ) : isAuthenticated ? (
          <span style={{ alignItems: 'center', display: 'flex', gap: 12 }}>
            <span>{user?.displayName || user?.email || 'Signed in'}</span>
            <button onClick={onSignOut} type="button">
              Sign out
            </button>
          </span>
        ) : (
          <button onClick={onSignIn} type="button">
            Sign in
          </button>
        )}
      </div>
    </header>
  )
}
