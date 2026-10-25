// Run the supports-hyperlinks package against this process's environment.
// Usage: node detect.mjs <node_modules dir> <platform> <tty 0|1>
import { pathToFileURL } from 'node:url';
import path from 'node:path';
const [modules, platform, tty] = process.argv.slice(2);
process.argv.length = 2;
Object.defineProperty(process, 'platform', { value: platform });
const entry = path.join(modules, 'supports-hyperlinks', 'index.js');
const { createSupportsHyperlinks } = await import(pathToFileURL(entry).href);
const colorEntry = path.join(modules, 'supports-color', 'index.js');
const { createSupportsColor } = await import(pathToFileURL(colorEntry).href);
const stream = { isTTY: tty === '1' };
const color = Boolean(createSupportsColor(stream));
process.stdout.write(JSON.stringify({ hyperlinks: createSupportsHyperlinks(stream), color }));
