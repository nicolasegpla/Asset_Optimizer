import packageInfo from '../../package.json';

interface HeroSectionProps {
  backendStatus: 'checking' | 'online' | 'offline';
}

const APP_VERSION = packageInfo.version;

export function HeroSection({ backendStatus }: HeroSectionProps) {
  return (
    <section className="hero">
      <p className="eyebrow">Asset Optimizer</p>
      <h1>Prepare web-ready images without friction.</h1>
      <p className="description">
        Convert, compress, resize, and package image assets for websites, e-commerce,
        and digital products.
      </p>

      <div className="status-row">
        <span className={`badge badge-${backendStatus}`}>API: {backendStatus}</span>
        <span className="badge badge-neutral">v{APP_VERSION}</span>
        <span className="badge badge-neutral">Docker-ready monorepo</span>
      </div>
    </section>
  );
}