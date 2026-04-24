import { spawn } from "node:child_process";

export async function activate() {
  spawn("bash", ["-lc", "echo test"]);
}
