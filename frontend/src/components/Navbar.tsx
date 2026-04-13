interface NavbarProps {
  dark: boolean;
  onToggleTheme: () => void;
  search: string;
  onSearch: (val: string) => void;
  onResumeUpload: () => void;
}

export default function Navbar({ dark, onToggleTheme, search, onSearch, onResumeUpload }: NavbarProps) {
  return (
    <nav
      id="navbar"
      className="sticky top-0 z-50 flex items-center justify-between px-6 py-3 border-b"
      style={{ backgroundColor: 'var(--color-bg)', borderColor: 'var(--color-border)' }}
    >
      {/* Logo */}
      <div className="flex items-center gap-3">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-sm"
          style={{ backgroundColor: 'var(--color-accent)' }}
        >
          SJ
        </div>
        <h1 className="text-lg font-bold" style={{ color: 'var(--color-text)' }}>
          Startup Jobs
        </h1>
      </div>

      {/* Global Search */}
      <div className="flex-1 max-w-md mx-6">
        <input
          id="global-search"
          type="text"
          placeholder="Search companies, roles, founders..."
          value={search}
          onChange={(e) => onSearch(e.target.value)}
          className="w-full px-4 py-2 rounded-lg text-sm outline-none border"
          style={{
            backgroundColor: 'var(--color-card)',
            color: 'var(--color-text)',
            borderColor: 'var(--color-border)',
          }}
        />
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        {/* Resume Upload Button */}
        <button
          id="resume-upload-btn"
          onClick={onResumeUpload}
          className="resume-upload-btn px-4 py-2 rounded-lg text-xs font-semibold cursor-pointer flex items-center gap-1.5"
          style={{
            background: 'linear-gradient(135deg, var(--color-accent), var(--color-accent-light))',
            color: '#fff',
            border: 'none',
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" />
          </svg>
          Upload Resume
        </button>

        {/* Theme Toggle */}
        <button
          id="theme-toggle"
          onClick={onToggleTheme}
          className="w-10 h-10 rounded-lg flex items-center justify-center border cursor-pointer"
          style={{
            backgroundColor: 'var(--color-card)',
            borderColor: 'var(--color-border)',
            color: 'var(--color-text)',
          }}
          title={dark ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {dark ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="5" />
              <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
            </svg>
          )}
        </button>
      </div>
    </nav>
  );
}
