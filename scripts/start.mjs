import {spawn, spawnSync} from "node:child_process";
import {fileURLToPath} from "node:url";

const windows = process.platform === "win32";
const commands = windows ? [["py", "-3"], ["python"], ["python3"]] : [["python3"], ["python"]];
const python = commands.find(([executable, ...prefix]) => spawnSync(
  executable, [...prefix, "-c", "import sys; sys.exit(sys.version_info < (3, 9))"],
  {stdio: "ignore", windowsHide: true, timeout: 7000}
).status === 0);
if (!python) {
  console.error("Install Python 3.9 or newer, then reopen the launcher. See docs/SETUP.md.");
  process.exit(1);
}
const [executable, ...prefix] = python;
const requested = process.argv.slice(2);
const flags = requested.filter(value => value !== "--no-open");
if (!requested.includes("--no-open")) flags.push("--open");
const script = fileURLToPath(new URL("../office/server.py", import.meta.url));
const child = spawn(executable, [...prefix, script, ...flags], {stdio: "inherit"});
child.once("error", error => { console.error(error.message); process.exitCode = 1; });
child.once("exit", (code, signal) => { process.exitCode = signal ? 1 : code ?? 1; });
