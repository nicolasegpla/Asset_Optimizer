const CREATOR_LINKS = {
  EMAIL: 'mailto:stalloy@stalloy.io',
  SITE: 'https://stalloy.io',
} as const;

export function CreatorCard() {
  return (
    <section className="creator-card" aria-label="Project creator">
      <p className="creator-label">Created by</p>
      <h2 className="creator-name">Stalloy</h2>
      <p className="creator-description">
        Independent maker behind Asset Optimizer. Need custom product work or want to get in touch?
      </p>

      <div className="creator-links">
        <a className="creator-link" href={CREATOR_LINKS.SITE} target="_blank" rel="noreferrer">
          stalloy.io
        </a>
        <a className="creator-link" href={CREATOR_LINKS.EMAIL}>
          stalloy@stalloy.io
        </a>
      </div>
    </section>
  );
}
