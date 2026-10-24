// Feed each input string to a fresh @xterm/headless terminal and report, per printed cell,
// the character and the URI of the hyperlink it carries (null when none).
// Usage: node xterm_cells.cjs <node_modules dir>  (JSON array of strings on stdin)
const path = require('path');
const { Terminal } = require(path.join(process.argv[2], '@xterm', 'headless'));
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => { input += chunk; });
process.stdin.on('end', async () => {
  const cases = JSON.parse(input);
  const out = [];
  for (const text of cases) {
    const term = new Terminal({ cols: 4000, rows: 4, scrollback: 0, allowProposedApi: true });
    await new Promise((resolve) => term.write(text, resolve));
    const core = term._core;
    const links = core._oscLinkService;
    const cells = [];
    const buffer = term.buffer.active;
    for (let y = 0; y < buffer.length; y++) {
      const line = buffer.getLine(y);
      for (let x = 0; x < line.length; x++) {
        const view = line.getCell(x);
        const chars = view.getChars();
        if (!chars) continue;
        const cell = view._cell || view;
        const urlId = cell.extended ? cell.extended.urlId : 0;
        const data = urlId ? links.getLinkData(urlId) : undefined;
        cells.push([chars, data ? data.uri : null]);
      }
    }
    out.push(cells);
    term.dispose();
  }
  process.stdout.write(JSON.stringify(out));
});
