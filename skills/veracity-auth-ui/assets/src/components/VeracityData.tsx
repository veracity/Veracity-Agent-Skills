import { useEffect, useState } from 'react'

import {
  VeracityApplication,
  VeracityService,
  getMyApplications,
  getMyServices,
} from '../api/veracity'

// Renders the optional Veracity API results. `showV3` / `showV4` are set at scaffold
// time based on whether the BFF actually exposes the V3 / V4 endpoints, so the app
// never calls an endpoint that does not exist.
interface VeracityDataProps {
  isAuthenticated: boolean
  showV3: boolean
  showV4: boolean
}

// Best-effort display label across the loosely-typed Veracity responses.
function label(item: Record<string, unknown>): string {
  return (
    (item.name as string) ??
    (item.serviceName as string) ??
    (item.title as string) ??
    (item.id as string) ??
    (item.serviceId as string) ??
    JSON.stringify(item)
  )
}

export default function VeracityData({ isAuthenticated, showV3, showV4 }: VeracityDataProps) {
  const [services, setServices] = useState<VeracityService[] | undefined>(undefined)
  const [applications, setApplications] = useState<VeracityApplication[] | undefined>(undefined)

  useEffect(() => {
    if (!isAuthenticated) return
    if (showV3) void getMyServices().then((r) => setServices(r ?? []))
    if (showV4) void getMyApplications().then((r) => setApplications(r ?? []))
  }, [isAuthenticated, showV3, showV4])

  if (!isAuthenticated || (!showV3 && !showV4)) return null

  return (
    <section style={{ marginTop: 24 }}>
      {showV3 && (
        <div>
          <h2>My Veracity services (V3)</h2>
          {services === undefined ? (
            <p>Loading services…</p>
          ) : services.length === 0 ? (
            <p>No services found.</p>
          ) : (
            <ul>
              {services.map((s, i) => (
                <li key={i}>{label(s)}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      {showV4 && (
        <div>
          <h2>My applications (V4)</h2>
          {applications === undefined ? (
            <p>Loading applications…</p>
          ) : applications.length === 0 ? (
            <p>No applications found.</p>
          ) : (
            <ul>
              {applications.map((a, i) => (
                <li key={i}>{label(a)}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  )
}
