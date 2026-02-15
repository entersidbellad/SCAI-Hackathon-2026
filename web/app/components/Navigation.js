'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function Navigation() {
  const pathname = usePathname();

  const links = [
    { href: '/', label: 'Leaderboard' },
    { href: '/explore', label: 'Explorer' },
    { href: '/reliability', label: 'Judges' },
    { href: '/methodology', label: 'Method' },
    { href: '/why-it-matters', label: 'Why It Matters' },
    { href: '/run-your-case', label: 'Run Your Case' },
  ];

  return (
    <nav className="nav">
      <div className="nav-inner">
        <Link href="/" className="nav-brand">
          <span className="sigma">∑</span>VAL
        </Link>
        <ul className="nav-links">
          {links.map(({ href, label }, index) => (
            <li key={href} style={{ display: 'flex', alignItems: 'center' }}>
              {index > 0 && <span className="nav-sep">/</span>}
              <Link href={href} className={`nav-link ${pathname === href ? 'active' : ''}`}>
                {label}
              </Link>
            </li>
          ))}
        </ul>
        <label className="nav-mobile-select-wrap">
          <span className="nav-mobile-label">Section</span>
          <select
            className="nav-mobile-select"
            value={pathname}
            onChange={(event) => {
              window.location.assign(event.target.value);
            }}
            aria-label="Navigate to section"
          >
            {links.map(({ href, label }) => (
              <option key={href} value={href}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>
    </nav>
  );
}
