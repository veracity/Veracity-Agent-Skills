import WelcomeExperience from './components/WelcomeExperience'

// === Baseline app shell ===
// The scaffold ships a single welcome page. The project name is injected at scaffold
// time and passed to the presentation as a prop, so design-system-generated
// presentation files need no placeholder substitution of their own.
//
// Skills that build ON TOP of this baseline (e.g. veracity-auth-ui) replace this
// shell with their own orchestration (hooks, providers) while keeping the same
// presentation-only contract for the UI.
const PROJECT_NAME = '{{projectName}}'

export default function App() {
  return <WelcomeExperience projectName={PROJECT_NAME} />
}
