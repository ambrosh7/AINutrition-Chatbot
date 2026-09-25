export function AppHeader() {
  return (
    <header className="app-header">
      <div className="header-left">
        <div className="brand-block">
          <div className="brand-mark" aria-hidden>
            <span className="material-symbols-outlined">nutrition</span>
          </div>
          <div className="brand-copy">
            <div className="brand-title-row">
              <span className="brand-name">Nutrition Assistant</span>
              <span className="brand-badge">m1</span>
            </div>
            <span className="brand-sub">Food, nutrition & food safety</span>
          </div>
        </div>
        <div className="header-divider" aria-hidden />
        <div className="status-pill">
          <span className="status-dot" aria-hidden />
          <span>Clinical Evidence Engine • Ready</span>
        </div>
      </div>
      <div className="header-right">
        <nav className="nav-tabs" aria-label="Primary">
          <button type="button" className="nav-tab active" aria-current="page">
            Consultation
          </button>
          <button type="button" className="nav-tab" disabled title="Milestone 2">
            Databases
          </button>
          <button type="button" className="nav-tab" disabled title="Milestone 2">
            Standards
          </button>
        </nav>
        <div className="header-avatar-wrap">
          <div className="header-avatar" aria-hidden>
            <span className="material-symbols-outlined">person</span>
          </div>
        </div>
      </div>
    </header>
  );
}
