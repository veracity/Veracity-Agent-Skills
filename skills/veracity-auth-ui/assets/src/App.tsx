import LoginExperience from './components/LoginExperience'
import { useAuth } from './hooks/useAuth'

// === Core auth orchestration — keep this here, NOT in the presentation layer. ===
// useAuth owns the /auth check, the /api/me fetch, and the sign-in/out navigation.
// The design-system UI (LoginExperience) is a dumb, prop-driven adapter that must
// never call auth endpoints directly. projectName and the V3/V4 flags are passed
// down as props/constants, so design-system-generated presentation files need no
// placeholder substitution of their own.
const PROJECT_NAME = '{{projectName}}'
const SHOW_V3 = __V3_ENABLED__
const SHOW_V4 = __V4_ENABLED__
// When true, a signed-in user is checked against the BFF policy/validate endpoint on
// load and redirected if they must accept the latest Veracity terms / lack a subscription.
const ENABLE_POLICY_CHECK = __POLICY_ENABLED__

export default function App() {
  const auth = useAuth({ enablePolicyCheck: ENABLE_POLICY_CHECK })

  return (
    <LoginExperience
      projectName={PROJECT_NAME}
      loading={auth.loading}
      isAuthenticated={auth.isAuthenticated}
      user={auth.user}
      onSignIn={auth.signIn}
      onSignOut={auth.signOut}
      showV3={SHOW_V3}
      showV4={SHOW_V4}
    />
  )
}
