import type { Claim } from "../types/chat";

type Props = {
  claims: Claim[] | undefined;
  mobileOpen: boolean;
};

function nonNullSources(claims: Claim[] | undefined): Claim[] {
  if (!claims) return [];
  return claims.filter((claim) => claim.source != null);
}

export function SourcesPanel({ claims, mobileOpen }: Props) {
  const sourced = nonNullSources(claims);
  const claimCount = claims?.length ?? 0;
  const linkedCount = sourced.length;

  return (
    <aside
      className={`sources-panel${mobileOpen ? "" : " mobile-hidden"}`}
      aria-label="Sources"
    >
      <div className="sources-header">
        <div className="sources-header-left">
          <span className="material-symbols-outlined">menu_book</span>
          <h2>Sources & Citations</h2>
        </div>
        <span className="sources-linked">{linkedCount} Linked</span>
      </div>

      {linkedCount === 0 ? (
        <div className="sources-body">
          <div className="sources-empty-icon" aria-hidden>
            <span className="material-symbols-outlined">nutrition</span>
          </div>
          <div className="sources-empty-copy">
            <h3>Citations will appear here</h3>
            <p>
              Sources will appear here in Milestone 2. When evidence is cited,
              publication references and links will resolve in this panel.
            </p>
            {claimCount > 0 ? (
              <p>
                This reply has {claimCount} claim
                {claimCount === 1 ? "" : "s"} with source still null.
              </p>
            ) : null}
          </div>
          <div className="sources-blueprint" aria-hidden>
            <div className="sources-blueprint-top">
              <span>Preview Blueprint</span>
              <span>Schema ID #204</span>
            </div>
            <div className="sources-blueprint-card">
              <div className="blueprint-meta">
                <span>PMID: —</span>
                <span>Pending</span>
              </div>
              <span className="blueprint-title">
                Citation card reserved for Milestone 2
              </span>
              <span className="blueprint-snippet">
                Peer-reviewed literature, USDA FoodData Central rows, and DOI
                links will populate this structure when retrieval is enabled.
              </span>
              <div className="blueprint-foot">
                <span className="blueprint-doi">doi: —</span>
                <span className="blueprint-match">Match: Claim —</span>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="sources-body has-claims">
          <ul className="sources-claim-list">
            {sourced.map((claim, index) => (
              <li key={`${claim.text}-${index}`} className="sources-claim-card">
                <header>
                  <span>CLAIM #{String(index + 1).padStart(2, "0")}</span>
                  <span>Linked</span>
                </header>
                <p>{claim.text}</p>
                <pre>{JSON.stringify(claim.source, null, 2)}</pre>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="sources-footer">
        <div className="sources-footer-row">
          <span>Index Cache</span>
          <span>PubMed Central • USDA-FDC</span>
        </div>
        <div className="sources-progress" aria-hidden>
          <span />
        </div>
        <span className="sources-sync">Milestone 1 • sources empty</span>
      </div>
    </aside>
  );
}
