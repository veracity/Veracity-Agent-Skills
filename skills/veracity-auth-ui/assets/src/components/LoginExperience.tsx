import { CurrentUser } from '../api/auth'
import LoginHeader from './LoginHeader'
import VeracityData from './VeracityData'

// === UI CONTRACT — the design-system adapter ===
// Every design system (ShadCN, design.md, or a custom one) implements this single
// component as a PURE, PROP-DRIVEN view. It is the only piece that changes between
// design systems; the auth core (App.tsx, useAuth, api/) stays the same.
//
// Rules for any implementation of this contract:
//   - Render the same login states: a Sign in button when signed out; the user's
//     name + a Sign out control when signed in; a loading state while checking.
//   - Trigger sign-in / sign-out ONLY via the `onSignIn` / `onSignOut` callbacks.
//   - NEVER call /auth, /api/me, /auth/challenge or /signout directly, and NEVER
//     add a global fetch interceptor.
//   - Show the optional Veracity data via <VeracityData>, gated by showV3/showV4.
//   - Stay presentation-only: receive everything via props; do not import the auth
//     hook or trigger navigation yourself.
//
// This plain, inline-styled version is the fallback/reference implementation.
export interface LoginExperienceProps {
  projectName: string
  loading: boolean
  isAuthenticated: boolean
  user: CurrentUser | null
  onSignIn: () => void
  onSignOut: () => void
  showV3: boolean
  showV4: boolean
}

export default function LoginExperience({
  projectName,
  loading,
  isAuthenticated,
  user,
  onSignIn,
  onSignOut,
  showV3,
  showV4
}: LoginExperienceProps) {
  return (
    <div>
      <LoginHeader
        projectName={projectName}
        loading={loading}
        isAuthenticated={isAuthenticated}
        user={user}
        onSignIn={onSignIn}
        onSignOut={onSignOut}
      />
      <main style={{ padding: 24 }}>
        <h1>Welcome to {projectName}</h1>
        {loading ? (
          <p>Checking your sign-in status…</p>
        ) : isAuthenticated ? (
          <p>You are signed in{user?.email ? ` as ${user.email}` : ''}.</p>
        ) : (
          <p>You are not signed in. Use the Sign in button to authenticate with Veracity.</p>
        )}
        <VeracityData isAuthenticated={isAuthenticated} showV3={showV3} showV4={showV4} />
      </main>
    </div>
  )
}
