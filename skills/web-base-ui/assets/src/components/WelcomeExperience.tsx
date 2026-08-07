import AppHeader from './AppHeader'

// === UI CONTRACT — the design-system adapter ===
// Every design system (ShadCN, design.md, MUI, or a custom one) implements this
// single component as a PURE, PROP-DRIVEN view. It is the only piece that changes
// between design systems; the app shell (App.tsx) stays the same.
//
// Rules for any implementation of this contract:
//   - Render a header with the project name and a welcome page body.
//   - Stay presentation-only: receive everything via props; do not fetch data or
//     own application state.
//
// This plain, inline-styled version is the fallback/reference implementation.
export interface WelcomeExperienceProps {
  projectName: string
}

export default function WelcomeExperience({ projectName }: WelcomeExperienceProps) {
  return (
    <div>
      <AppHeader projectName={projectName} />
      <main style={{ padding: 24 }}>
        <h1>Welcome to {projectName}</h1>
        <p>
          This is your new {projectName} app. Start building by editing the components in{' '}
          <code>src/components/</code>.
        </p>
      </main>
    </div>
  )
}
