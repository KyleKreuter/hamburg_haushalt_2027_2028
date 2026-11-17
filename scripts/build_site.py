"""Build the standalone static site from the dashboard page and its data files.

The dashboard page reads its data and view state through a small host API (`window.dash`).
This script provides that API, so the page runs on any static web server:
the data comes from the JSON files next to index.html, and the view state lives in
the URL hash so that a view can be shared as a link.

Usage: python3 -I scripts/build_site.py <dashboard_dir> <out_dir>

If <dashboard_dir>/vendor/d3.min.js exists, the site serves d3 itself; otherwise it
loads d3 from jsDelivr.
"""

import os
import shutil
import sys

DATASETS = ["eckwerte", "einzelplaene", "produkte", "finanzbericht", "kostenarten", "kennzahlen"]
D3_VERSION = "7.9.0"
IMPRESSUM = "https://kyle.vermittler.dev"
# Controller named in the privacy notice (Art. 13 GDPR); taken from the public page at IMPRESSUM.
VERANTWORTLICH = 'Kyle Kreuter<br>E-Mail: <a href="mailto:kyle.kreuter@outlook.de">kyle.kreuter@outlook.de</a>'
STAND = "17. November 2026"

RUNTIME = r"""
<script>
window.dash = (() => {
  const defaults = { jahr: '2027', vgl: '', art: 'ausgaben', sicht: 'epl', chart: 'saeulen', pfad: '', fokus: '' };
  const fromHash = () => {
    const q = new URLSearchParams(location.hash.slice(1));
    const p = { ...defaults };
    for (const k of Object.keys(defaults)) if (q.has(k)) p[k] = q.get(k);
    return p;
  };
  const toHash = (p) => {
    const q = new URLSearchParams();
    for (const k of Object.keys(defaults)) if (p[k] !== defaults[k]) q.set(k, p[k]);
    const s = q.toString();
    history.replaceState(null, '', s ? `#${s}` : location.pathname + location.search);
  };
  let params = fromHash();
  const store = {}; const calcs = []; const draws = {}; const listeners = [];
  let state = 'loading';
  const data = (id) => (state === 'error' ? { status: 'error', error: 'Die Daten konnten nicht geladen werden.' }
    : id in store ? { status: 'ok', data: store[id] } : { status: 'loading' });
  function recompute() { for (const c of calcs) store[c.id] = c.fn(...c.inputs.map((i) => store[i])); }
  function render(name) {
    document.querySelectorAll(`[data-draw="${name}"]`).forEach((el) => {
      const d = draws[name];
      try {
        if (typeof d === 'function') d(el);
        else { if (!el.__st) { el.replaceChildren(); el.__st = d.mount(el) || {}; } d.update(el, el.__st); }
      } catch (e) { console.error(name, e); }
    });
  }
  function all() { if (state === 'ok') recompute(); for (const n in draws) render(n); listeners.forEach((f) => f()); }
  window.addEventListener('hashchange', () => { params = fromHash(); all(); });
  let t;
  window.addEventListener('resize', () => { clearTimeout(t); t = setTimeout(all, 120); });
  return {
    calc: (id, o) => calcs.push({ id, ...o }),
    draw: (name, d) => { if (d === undefined) { render(name); return; } draws[name] = d; },
    data,
    params: () => ({ ...params }),
    setParams: (c) => { params = { ...params, ...c }; toHash(params); all(); },
    resetParams: () => { params = { ...defaults }; toHash(params); all(); },
    onData: (f) => listeners.push(f),
    _load: async () => {
      try {
        const rows = await Promise.all(__DATASETS__.map(async (f) => {
          const r = await fetch(`${f}.json`);
          if (!r.ok) throw new Error(`${f}: ${r.status}`);
          return (await r.json()).rows;
        }));
        __DATASETS__.forEach((f, i) => { store[f] = rows[i]; });
        state = 'ok';
      } catch (e) {
        console.error(e);
        state = 'error';
      }
      all();
    },
  };
})();
</script>
"""

STYLE = """
<style>
  :root { --font-sans: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; color-scheme: dark; }
  html { background: #0b1622; }
  body { margin: 0; padding: 16px; background: #0b1622; font-family: var(--font-sans); -webkit-text-size-adjust: 100%; }
  .site { max-width: 1480px; margin: 0 auto; }
  .site-foot { max-width: 1480px; margin: 0 auto; padding: 28px clamp(18px, 3.2vw, 44px) 12px; display: flex; flex-wrap: wrap; gap: 8px 24px; justify-content: space-between; color: #8ea3b8; font-size: 13px; line-height: 1.5; }
  .site-foot p { margin: 0; max-width: 72ch; }
  .site-foot a { color: #d7e2ec; text-underline-offset: 3px; }
  .site-links { display: flex; gap: 20px; }
  .site-foot a:hover { color: #fff; }
  /* Phones: the page runs edge to edge; the dashboard keeps its own inner padding. */
  @media (max-width: 600px) {
    body { padding: 0 0 16px; }
    .site .hx { border-radius: 0; }
    /* Smaller type keeps each footer sentence on one line down to 360 px. */
    .site-foot { padding: 24px 16px 8px; font-size: clamp(10.5px, 2.9vw, 13px); }
  }
</style>
"""

HEAD = (
    '<!doctype html>\n<html lang="de">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
    '<meta name="theme-color" content="#0b1622">\n'
)

FOOTER = f"""
<footer class="site-foot">
  <p>Unabhängige Auswertung der veröffentlichten Haushaltspläne.<br>Kein Angebot der Freien und Hansestadt Hamburg.</p>
  <nav class="site-links" aria-label="Rechtliches">
    <a href="datenschutz.html">Datenschutz</a>
    <a href="{IMPRESSUM}" rel="noopener">Impressum</a>
  </nav>
</footer>
"""

PRIVACY_STYLE = """
<style>
  .doc { max-width: 72ch; margin: 0 auto; padding: 48px clamp(18px, 3.2vw, 44px) 24px; color: #d7e2ec; font-size: 16px; line-height: 1.6; }
  .doc h1 { color: #fff; font-size: clamp(28px, 4vw, 40px); line-height: 1.15; margin: 24px 0 8px; letter-spacing: -0.01em; }
  .doc h2 { color: #fff; font-size: 20px; line-height: 1.3; margin: 40px 0 8px; }
  .doc p, .doc ul { margin: 0 0 12px; }
  .doc ul { padding-left: 1.2em; }
  .doc li { margin-bottom: 4px; }
  .doc .doc-meta { color: #8ea3b8; font-size: 14px; }
  .doc a { color: #f6c445; text-underline-offset: 3px; }
  .doc a:hover { color: #fff; }
  .doc .doc-back { display: inline-block; font-size: 14px; font-weight: 600; text-decoration: none; }
  .doc .doc-back:hover { text-decoration: underline; }
</style>
"""

PRIVACY = """
<main class="doc">
  <a class="doc-back" href="./">← Zur Auswertung</a>
  <h1>Datenschutzerklärung</h1>
  <p class="doc-meta">Stand: __STAND__</p>

  <h2>Kurz gesagt</h2>
  <p>Diese Website setzt keine Cookies, nutzt keine Analyse- oder Trackingdienste und speichert nichts in Ihrem Browser. Sie lädt keine Inhalte von anderen Anbietern: Programmcode, Diagrammbibliothek und Haushaltsdaten kommen vom eigenen Server. Personenbezogene Daten entstehen nur beim technischen Abruf der Seite.</p>

  <h2>Verantwortlich</h2>
  <p>__VERANTWORTLICH__</p>

  <h2>Abruf der Website</h2>
  <p>Wenn Sie die Website aufrufen, überträgt Ihr Browser technisch notwendige Daten: Ihre IP-Adresse, Datum und Uhrzeit, die aufgerufene Adresse, die zuvor besuchte Seite (Referrer) sowie Browser und Betriebssystem (User-Agent). Ohne diese Daten kann die Seite nicht ausgeliefert werden.</p>
  <p>Rechtsgrundlage ist Art. 6 Abs. 1 lit. f DSGVO. Das berechtigte Interesse liegt darin, die Website sicher und funktionsfähig bereitzustellen.</p>

  <h2>Cloudflare</h2>
  <p>Alle Anfragen laufen über das Netzwerk der Cloudflare, Inc., 101 Townsend St., San Francisco, CA 94107, USA. Cloudflare leitet die Anfragen an den Server weiter, hält Inhalte zwischengespeichert und wehrt Angriffe ab. Dabei verarbeitet Cloudflare die oben genannten Daten, auch in den USA.</p>
  <p>Cloudflare ist nach dem EU-U.S. Data Privacy Framework zertifiziert. Für Datenübermittlungen an zertifizierte Unternehmen gilt der Angemessenheitsbeschluss der EU-Kommission vom 10. Juli 2023. Cloudflare verarbeitet die Daten als Auftragsverarbeiter nach Art. 28 DSGVO.</p>
  <p>Cloudflare bittet Ihren Browser außerdem, fehlgeschlagene Verbindungen an Cloudflare zu melden (Network Error Logging). Erfolgreiche Abrufe meldet der Browser nicht.</p>
  <p>Weitere Informationen: <a href="https://www.cloudflare.com/de-de/privacypolicy/" rel="noopener">Datenschutzerklärung von Cloudflare</a>.</p>

  <h2>Hosting</h2>
  <p>Der Server steht bei der OVH SAS, 2 rue Kellermann, 59100 Roubaix, Frankreich. Er nimmt Anfragen nur über Cloudflare entgegen und schreibt für diese Website keine Zugriffsprotokolle.</p>

  <h2>Speicherdauer</h2>
  <p>Auf dem Server dieser Website werden keine Zugriffsdaten gespeichert. Wie lange Cloudflare Daten aufbewahrt, regelt die Datenschutzerklärung von Cloudflare.</p>

  <h2>Ihre Rechte</h2>
  <p>Sie haben das Recht auf</p>
  <ul>
    <li>Auskunft über die verarbeiteten Daten (Art. 15 DSGVO),</li>
    <li>Berichtigung (Art. 16 DSGVO),</li>
    <li>Löschung (Art. 17 DSGVO),</li>
    <li>Einschränkung der Verarbeitung (Art. 18 DSGVO) und</li>
    <li>Widerspruch gegen die Verarbeitung aus Gründen, die sich aus Ihrer besonderen Situation ergeben (Art. 21 DSGVO).</li>
  </ul>
  <p>Sie können sich außerdem bei einer Datenschutz-Aufsichtsbehörde beschweren. Zuständig für Hamburg ist der Hamburgische Beauftragte für Datenschutz und Informationsfreiheit, Ludwig-Erhard-Straße 22, 20459 Hamburg.</p>
</main>
"""


def main(src, out):
    os.makedirs(out, exist_ok=True)
    page = open(os.path.join(src, "index.html"), encoding="utf-8").read()
    for f in DATASETS:
        shutil.copy(os.path.join(src, f + ".json"), os.path.join(out, f + ".json"))
    vendor = os.path.join(src, "vendor", "d3.min.js")
    if os.path.exists(vendor):
        shutil.copy(vendor, os.path.join(out, "d3.min.js"))
        # The ISC license requires its notice next to every copy of d3.
        license_d3 = os.path.join(src, "vendor", "LICENSE-d3.txt")
        if os.path.exists(license_d3):
            shutil.copy(license_d3, os.path.join(out, "LICENSE-d3.txt"))
        d3 ='<script src="d3.min.js"></script>'
    else:
        d3 = f'<script src="https://cdn.jsdelivr.net/npm/d3@{D3_VERSION}/dist/d3.min.js"></script>'
    runtime = RUNTIME.replace("__DATASETS__", repr(DATASETS))
    html = (
        HEAD
        + "<title>Hamburgs Haushalt 2027/2028</title>\n"
        '<meta name="description" content="Einnahmen, Ausgaben und Investitionen im Entwurf des Haushaltsplans 2027/2028 der Freien und Hansestadt Hamburg, nach Einzelplan, Aufgabe und Produkt.">\n'
        + d3 + "\n" + STYLE + "</head>\n<body>\n" + runtime
        + '<main class="site">\n' + page + "\n</main>\n" + FOOTER
        + "<script>dash._load();</script>\n</body>\n</html>\n"
    )
    open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(html)
    privacy = (
        HEAD + "<title>Datenschutz · Hamburgs Haushalt 2027/2028</title>\n"
        '<meta name="robots" content="noindex">\n'
        + STYLE + PRIVACY_STYLE + "</head>\n<body>\n"
        + PRIVACY.replace("__STAND__", STAND).replace("__VERANTWORTLICH__", VERANTWORTLICH)
        + FOOTER + "</body>\n</html>\n"
    )
    open(os.path.join(out, "datenschutz.html"), "w", encoding="utf-8").write(privacy)
    print(f"{out}: {', '.join(sorted(os.listdir(out)))}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
