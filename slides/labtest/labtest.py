#!/usr/bin/env python3
"""Test the hands-on labs of a deck on a lab cluster.

One file, three roles (standard library only, so it runs on a laptop and on
a lab node without installs):

  plan  (laptop) Read a deck manifest and its Markdown files, and list the
        commands of every .lab[] block, in deck order, with file:line.
        Also warns about commands that will probably hang. No lab needed.
  run   (laptop) Copy this file and the plan to node1 of a lab, start
        "exec" there in the background, show progress, then download the
        results to runs/<run-id>/.
  exec  (node1, as the student user) Type each command into a private tmux
        session, like a student, and record what happened.

How "exec" knows that a command is done: after each command it types
`echo __LTRC_$?_$((0+N))`. When "__LTRC_<rc>_<N>" shows in the output, the
command is done and <rc> is its exit code. This works in nested shells too
(ssh node2, kubectl exec -it ... sh). Lines with __LTRC_ are removed from
the logs.

Directives (in the Markdown, inside .lab[]; hide them from students with an
HTML comment, e.g. <!-- ```wait Running``` -->). A directive applies to the
command block just before it.

  wait TEXT       Do not wait for the prompt; pass when TEXT shows (60s).
  longwait TEXT   Same, 600s.
  key KEY         Send one tmux key: ^C, ^D, ^J (Enter), ^[ (Escape), Space.
  keys TEXT       Type TEXT (no Enter).
  tmux ARGS       Run a tmux command in the session (split-pane -v, ...).
  hide            (block) Run these commands; students do not see them.
  copy REGEX      Remember the last match of REGEX in the output.
  paste           Type what "copy" remembered.
  copypaste REGEX copy, then paste.
  open URL        Check the URL with curl from node1 (warning only).
  check, look     No action (the exit code is always checked).
  expect-fail     The command must fail (exit code not 0). For slides that
                  show an error on purpose.
  timeout SECONDS Time limit for the command (default 120).
  skip REASON     Do not run the command; report it as SKIP.

A command block followed by key/keys/tmux is "interactive" (vim, k9s,
logs -f, ...): it is typed, the screen is recorded when it stops changing,
and no exit code is expected. Before the next normal command, the runner
checks that the program has ended. If not, the interactive step fails
("still running") and the runner sends ^C, Escape and :q! to recover.
"""

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SLIDES = os.path.dirname(HERE)
REPO = os.path.dirname(SLIDES)
REMOTE_DIR = ".labtest"
DEFAULT_TIMEOUT = 120
WAIT_TIMEOUT = 60
LONGWAIT_TIMEOUT = 600

# Commands that usually do not return. A command like this with no
# key/keys/wait directive after it will hang until its timeout.
# Programs match only at the start of a command (not inside a grep string).
# Nested shells (ssh node2, sudo -i, sh) are not here: the end marker works
# in them.
LONG_RUNNING = re.compile(
    r"((?:^|[;&|(]\s*|\bsudo\s+(?:-\S+\s+)*)(?:watch|vim?|nano|k9s|stern|less|more|top)\b|"
    r"\s-w\b|--watch\b|\blogs\b.*\s-f\b|\blogs\b.*--follow|\bkubectl\s+edit\b|"
    r"\b(?:kubectl|docker)\s+(?:run|exec)\b(?=.*\s(?:-\w*t\w*|--tty)\b)(?:.*\s(?:/bin/)?(?:ba)?sh|"
    r"(?:\s+(?:-\S+|--image\s+\S+))*\s+[\w.-]+(?:\s+(?:-\S+|--image\s+\S+))*)$|"
    r"\battach\b|\bport-forward\b|"
    r"^while\b)")
MODIFIERS = ("wait", "longwait", "expect-fail", "timeout", "skip", "check",
             "look")
KEYISH = re.compile(r"^(\^.|C-.|M-.|Escape|Enter|Space|Tab|BSpace|Up|Down|"
                    r"Left|Right|PageUp|PageDown|Home|End|F\d+)$")


# ---------------------------------------------------------------- plan ---

def read_manifest(path):
    """Minimal reader for our deck manifests (no PyYAML on the laptop)."""
    meta, files, exclude = {}, [], []
    section = None
    for raw in open(path):
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^(\w+):\s*(.*)$", line)
        if m:
            section = m.group(1)
            meta[section] = m.group(2).strip().strip("\"'")
            continue
        m = re.match(r"^\s*-\s*(\S+)\s*$", line)
        if not m:
            continue
        if section == "exclude":
            exclude.append(m.group(1))
        elif section == "content" and m.group(1).endswith(".md"):
            files.append(m.group(1))
    return meta, files, exclude


def atat(text, meta):
    for key in ("gitrepo", "gitbranch", "slides", "chat"):
        text = text.replace("@@{}@@".format(key.upper()), meta.get(key, ""))
    return text


def parse_markdown(relpath, exclude, meta):
    """Return the raw snippets of every .lab[] block of one Markdown file."""
    lines = open(os.path.join(SLIDES, relpath)).read().split("\n")
    snippets = []
    title, classes, in_props, in_notes, in_lab = "", [], True, False, False
    block = None
    for n, line in enumerate(lines, 1):
        if block is not None:
            if re.match(r"^```\s*(-->)?$", line.strip()):  # Also "``` -->" (hidden block)
                body = "\n".join(l[block["indent"]:] if l[:block["indent"]].strip() == "" else l.lstrip()
                                 for l in block["lines"])
                snippets.append(dict(block, data=body.strip("\n")))
                block = None
            else:
                block["lines"].append(line)
            continue
        if line == "---":
            title, classes, in_props, in_notes, in_lab = "", [], True, False, False
            continue
        if line == "--":
            continue
        if in_props:
            m = re.match(r"^(\w+):\s*(.*)$", line)
            if m:
                if m.group(1) == "class":
                    classes = [c for c in re.split(r"[,\s]+", m.group(2)) if c]
                if m.group(1) == "exclude" and m.group(2).strip() == "true":
                    classes.append("__exclude__")
                continue
            if line.strip():
                in_props = False
        if line.strip() == "???":
            in_notes = True
        if in_notes:
            continue
        m = re.match(r"^#{1,3} (.+)", line)
        if m and not title:
            title = m.group(1).strip()
        if line.startswith(".lab["):
            in_lab = True
            continue
        if in_lab and line.startswith("]"):
            in_lab = False
            continue
        if not in_lab:
            continue
        common = dict(file=relpath, line=n, title=title,
                      excluded=any(c in exclude or c == "__exclude__" for c in classes))
        # Single-line snippet, hidden or not: <!-- ```wait foo``` --> or ```key ^C```
        # (Text after the closing ``` is ignored, e.g. "```key ^[``` ]".)
        m = re.match(r"^\s*(?:<!--\s*)?```([\w-]+)(?:[ \t]+(.*?))?```", line)
        if m:
            snippets.append(dict(common, method=m.group(1), data=atat(m.group(2) or "", meta),
                                 hidden=line.lstrip().startswith("<!--")))
            continue
        # Fenced block, or hidden block: "<!-- ```hide" ... "``` -->".
        m = re.match(r"^(\s*)(<!--\s*)?```([\w-]*)\s*$", line)
        if m:
            block = dict(common, method=m.group(3) or "text", indent=len(m.group(1)),
                         lines=[], hidden=bool(m.group(2)))
            continue
    # The fenced block text may contain @@ strings; replace them now.
    for s in snippets:
        s.pop("lines", None)
        s.pop("indent", None)
        s["data"] = atat(s["data"], meta)
    return snippets


def build_plan(snippets):
    """Turn raw snippets into steps: fold modifiers into the command before."""
    steps = []
    for s in snippets:
        method, data = s["method"], s["data"]
        prev = steps[-1] if steps else None
        prev_cmd = prev if prev and prev["method"] in ("bash", "hide") else None
        if method in ("yaml", "json", "text", "console", "plaintext"):
            continue  # Shown to students, not run.
        if method in MODIFIERS and prev_cmd is not None and s["file"] == prev_cmd["file"]:
            if method in ("wait", "longwait"):
                prev_cmd["wait"] = data
                prev_cmd["timeout"] = max(prev_cmd.get("timeout") or 0,
                                          LONGWAIT_TIMEOUT if method == "longwait" else WAIT_TIMEOUT)
            elif method == "expect-fail":
                prev_cmd["expect_fail"] = True
            elif method == "timeout":
                prev_cmd["timeout"] = int(data)
            elif method == "skip":
                prev_cmd["skip"] = data or "skip directive"
            continue
        # A long-running program (vim, logs -f, ...) followed by keys is
        # interactive. A plain command followed by keys (e.g. ^D to close a
        # tmux pane) still returns, so we keep checking its exit code.
        if method in ("key", "keys", "tmux") and prev_cmd is not None and not prev_cmd.get("wait") \
                and LONG_RUNNING.search(oneline(split_commands(prev_cmd["data"].replace("`", ""))[-1])):
            prev_cmd["interactive"] = True
        step = dict(s, method=method, data=data)
        if method in ("bash", "hide"):
            step["data"] = data.replace("`", "")  # Backticks only highlight text on slides.
        steps.append(step)
    for i, step in enumerate(steps, 1):
        step["id"] = i
        if step["method"] in ("bash", "hide"):
            step["mode"] = "interactive" if step.get("interactive") else (
                "wait" if step.get("wait") else "normal")
            step.setdefault("timeout", DEFAULT_TIMEOUT)
    return steps


def select(steps, only, start, stop):
    def match(step, pattern):
        f, _, ln = pattern.partition(":")
        return (step["file"] == f or step["file"].endswith("/" + f)) and (
            not ln or step["line"] >= int(ln))
    out, on, in_stop = [], not start, False
    for step in steps:
        if start and not on and match(step, start):
            on = True
        if stop:
            if match(step, stop.split(":")[0]):
                in_stop = True
            elif in_stop:
                break  # First step after the --to file.
        if on and (not only or any(match(step, p.split(":")[0]) for p in only)):
            out.append(step)
    return out


def oneline(cmd):
    """Join lines that end with a backslash, for pattern checks."""
    return re.sub(r"\\\n\s*", " ", cmd).strip()


# Text that a student must replace before running the command.
PLACEHOLDER = re.compile(r"(x{4,}|y{4,}|z{4,}|\bnode[XN]\b|<[A-Za-z][\w-]*>|\w\.\.\.(?!\.)|"
                         r"\b[A-Z]{2,}-[A-Z]{2,}\b)")
ERROR_COMMENT = re.compile(r"#.*\b(error|fails?|forbidden|denied)\b", re.IGNORECASE)


def lint(steps):
    """Return {kind: [(step, text)]} for problems found without a lab."""
    found = {"Probably hangs (no key/keys/wait directive after it)": [],
             "Placeholder to replace (add skip + a hidden real command)": [],
             "Comment says it fails, but no expect-fail directive": []}
    hangs, holders, errors = found.values()
    for step in steps:
        if step["method"] not in ("bash", "hide") or step.get("skip"):
            continue
        for cmd in split_commands(step["data"]):
            cmd = oneline(cmd)
            if step["mode"] == "normal" and LONG_RUNNING.search(cmd) and not cmd.endswith("&"):
                hangs.append((step, cmd))
            m = PLACEHOLDER.search(cmd)
            if m:
                holders.append((step, cmd))
        if ERROR_COMMENT.search(step["data"]) and not step.get("expect_fail") and not step.get("wait"):
            errors.append((step, step["data"]))
    return found


def make_plan(deck, only=(), start=None, stop=None):
    meta, files, exclude = read_manifest(os.path.join(SLIDES, deck))
    snippets = []
    for f in files:
        if os.path.isfile(os.path.join(SLIDES, f)):
            snippets += parse_markdown(f, exclude, meta)
    steps = [s for s in build_plan(snippets) if not s["excluded"]]
    steps = select(steps, only, start, stop)
    return dict(deck=deck, created=time.strftime("%Y-%m-%d %H:%M:%S"), steps=steps)


def short(text, width=90):
    text = " ⏎ ".join(l.strip() for l in text.strip().split("\n"))
    return text if len(text) <= width else text[:width - 1] + "…"


def cmd_plan(args):
    plan = make_plan(args.deck, args.only, args.start, args.stop)
    steps = plan["steps"]
    if args.output:
        json.dump(plan, open(args.output, "w"), indent=1)
    per_file = {}
    for s in steps:
        per_file.setdefault(s["file"], [0, 0])
        per_file[s["file"]][0 if s["method"] in ("bash", "hide") else 1] += 1
    print("{}: {} steps, {} commands, {} files".format(
        args.deck, len(steps), sum(v[0] for v in per_file.values()), len(per_file)))
    if args.verbose:
        for s in steps:
            extra = " ".join(k for k in ("interactive", "expect_fail") if s.get(k))
            if s.get("wait"):
                extra += " wait=" + repr(s["wait"])
            if s.get("skip"):
                extra += " SKIP"
            print("  {:>4} {}:{} {:<8} {} {}".format(
                s["id"], s["file"], s["line"], s["method"], short(s["data"], 70), extra))
    else:
        for f, (cmds, others) in per_file.items():
            print("  {:<40} {:>3} commands {:>3} directives".format(f, cmds, others))
    for kind, items in lint(steps).items():
        if items:
            print("\n{}: {}".format(kind, len(items)))
            for step, text in items:
                print("  {}:{}  {}".format(step["file"], step["line"], short(text, 80)))


# ---------------------------------------------------------------- exec ---

# Shell compound commands that continue on the next lines until their end
# word: for/while/until ... done, if ... fi, case ... esac.
COMPOUND_OPEN = re.compile(r"(?:^|[;&|(]\s*|\b(?:then|do|else)\s+)(for|while|until|if|case)\b")
COMPOUND_CLOSE = re.compile(r"(?:^|[;&|]\s*|\s)(done|fi|esac)\b")


def split_commands(text):
    """Split a block into the commands that a student types one at a time."""
    cmds, cur, heredoc, depth = [], [], None, 0
    for line in text.split("\n"):
        cur.append(line)
        if heredoc:
            if line.strip() == heredoc:
                heredoc = None
            else:
                continue
        else:
            m = re.search(r"<<-?\s*['\"]?(\w+)['\"]?", line)
            if m:
                heredoc = m.group(1)
                continue
        code = line.strip().split(" #")[0]
        depth += len(COMPOUND_OPEN.findall(code)) - len(COMPOUND_CLOSE.findall(code))
        if depth > 0 or re.search(r"(\\|\||&&|\|\||\{|\()\s*$", line):
            continue
        depth = 0
        if "".join(cur).strip():
            cmds.append("\n".join(cur))
        cur = []
    if "".join(cur).strip():
        cmds.append("\n".join(cur))
    return cmds


class Term:
    """A private tmux server (socket "labtest"), so other sessions are safe."""

    def __init__(self):
        self.base = ["tmux", "-L", "labtest"]
        self.target = "lt"

    def tmux(self, *args, check=True):
        r = subprocess.run(self.base + list(args), capture_output=True, text=True)
        if check and r.returncode:
            raise RuntimeError("tmux {}: {}".format(" ".join(args), r.stderr.strip()))
        return r.stdout

    def start(self):
        self.tmux("kill-server", check=False)
        self.tmux("new-session", "-d", "-s", self.target, "-x", "200", "-y", "50",
                  "-c", os.path.expanduser("~"))
        self.tmux("set", "-g", "window-size", "manual")
        self.tmux("set", "-g", "history-limit", "1000000")
        time.sleep(2)

    def pos(self):
        hs, cy, alt = self.tmux("display", "-p", "-t", self.target,
                                "#{history_size} #{cursor_y} #{alternate_on}").split()
        return int(hs), int(cy), alt == "1"

    def mark(self):
        hs, cy, _ = self.pos()
        return hs + cy

    def since(self, mark):
        hs, cy, alt = self.pos()
        if alt:
            return self.screen()
        return self.tmux("capture-pane", "-p", "-J", "-t", self.target,
                         "-S", str(mark - hs), "-E", str(cy))

    def screen(self):
        return self.tmux("capture-pane", "-p", "-J", "-t", self.target)

    def type(self, text, enter=True):
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if line:
                self.tmux("send-keys", "-t", self.target, "-l", line)
            if enter or i < len(lines) - 1:
                self.tmux("send-keys", "-t", self.target, "Enter")

    def key(self, key):
        self.tmux("send-keys", "-t", self.target, key)

    def settle(self, quiet=1.0, maximum=10.0):
        last, stable_since, t0 = None, time.time(), time.time()
        while time.time() - t0 < maximum:
            now = self.screen()
            if now != last:
                last, stable_since = now, time.time()
            elif time.time() - stable_since >= quiet:
                return
            time.sleep(0.25)


def clean(text):
    lines = [l.rstrip() for l in text.split("\n") if "__LTRC_" not in l]
    # Drop the student prompt at the end ("[ip] (context) user@host dir" + "$").
    while lines and (not lines[-1] or lines[-1] == "$" or PROMPT.match(lines[-1])):
        lines.pop()
    return "\n".join(lines)


PROMPT = re.compile(r"^\[[\d.]+\] \(.*\) \S+@\S+")
ERRORISH = re.compile(r"(?i)(\berror\b|forbidden|not found|denied|refused|"
                      r"crashloopbackoff|imagepullbackoff|errimagepull|\bfailed\b|"
                      r"command not found|no such file)")


class Runner:

    def __init__(self, rundir):
        self.rundir = rundir
        self.plan = json.load(open(os.path.join(rundir, "plan.json")))
        self.term = Term()
        self.results = []
        self.pending = None   # Interactive/wait step whose program may still run.
        self.clipboard = ""
        self.group_mark = 0
        os.makedirs(os.path.join(rundir, "steps"), exist_ok=True)
        self.progress = open(os.path.join(rundir, "progress.log"), "a", buffering=1)
        self.counter = 0

    def probe(self, timeout):
        """Type the end marker; return the exit code, or None on timeout.

        A marker can get lost: keys typed while a nested session (ssh node2,
        kubectl exec) closes go to that session. So when no marker shows and
        the screen is quiet for 5s, type another one. Any of them counts: the
        first one that shows has the right exit code, because the shell runs
        them in the order they were typed.
        """
        mark = self.term.mark()
        ids = []

        def send():
            self.counter += 1
            ids.append(self.counter + 100000)
            self.term.type(" echo __LTRC_$?_$((0+{}))".format(ids[-1]))
        send()
        t0 = last_send = quiet_since = time.time()
        last_screen = None
        while time.time() - t0 < timeout:
            m = re.search(r"__LTRC_(\d+)_(?:{})\b".format("|".join(map(str, ids))),
                          self.term.since(mark))
            if m:
                return int(m.group(1))
            screen = self.term.screen()
            if screen != last_screen:
                last_screen, quiet_since = screen, time.time()
            elif time.time() - quiet_since >= 5 and time.time() - last_send >= 10 and len(ids) < 5:
                send()
                last_send = quiet_since = time.time()
            time.sleep(0.3)
        return None

    def ensure_prompt(self):
        """If the last interactive program still runs, fail it and recover."""
        if not self.pending:
            return
        step = self.pending
        self.pending = None
        rc = self.probe(15 if step["mode"] == "wait" else 5)
        if rc is not None:
            return
        res = next((r for r in self.results if r["id"] == step["id"]), None)
        reason = ("program still running before the next command "
                  "(missing key/keys directive?); sent ^C/Escape/:q! to recover")
        for keys in (["C-c"], ["Escape", ":q!", "Enter"], ["q"], ["C-d"]):
            for k in keys:
                self.term.tmux("send-keys", "-t", self.term.target,
                               *(["-l", k] if k.startswith(":") else [k]))
            time.sleep(1)
            if self.probe(5) is not None:
                break
        if res and res["status"] != "FAIL":
            res["status"], res["reason"] = "FAIL", reason
            self.write_log(step, res, res.get("output_tail", ""))
            self.report(step, res)

    def diagnostics(self):
        cmds = [
            "kubectl get pods -A -o wide --field-selector=status.phase!=Running,status.phase!=Succeeded",
            "kubectl get events -A --sort-by=.lastTimestamp | tail -n 15",
        ]
        out = []
        for c in cmds:
            r = subprocess.run(["bash", "-lc", c], capture_output=True, text=True, timeout=30)
            out.append("$ {}\n{}{}".format(c, r.stdout, r.stderr))
        return "\n".join(out)

    def run_command(self, step):
        """Run a bash/hide step. Return a result dict."""
        res = dict(id=step["id"], file=step["file"], line=step["line"],
                   title=step["title"], command=step["data"], mode=step["mode"])
        if step.get("skip"):
            return dict(res, status="SKIP", reason=step["skip"], output="")
        self.ensure_prompt()
        cmds = split_commands(step["data"])
        mark = self.group_mark = self.term.mark()
        t0 = time.time()
        rcs = []
        for i, cmd in enumerate(cmds):
            last = i == len(cmds) - 1
            self.term.type(cmd)
            if last and step["mode"] == "interactive":
                self.term.settle()
                self.pending = step
                return dict(res, status="PASS", reason="interactive: typed, screen recorded",
                            output=self.term.since(mark), screen=self.term.screen(),
                            seconds=round(time.time() - t0, 1))
            if last and step["mode"] == "wait":
                found = self.wait_for(step["wait"], mark, step["timeout"])
                self.pending = step
                out = self.term.since(mark)
                if found:
                    return dict(res, status="PASS", reason="found {!r}".format(step["wait"]),
                                output=out, seconds=round(time.time() - t0, 1))
                return dict(res, status="FAIL", output=out, seconds=round(time.time() - t0, 1),
                            reason="{!r} not shown after {}s".format(step["wait"], step["timeout"]))
            if cmd.strip() in ("exit", "logout"):
                self.term.settle(maximum=8)  # Let the nested session close first.
            rc = self.probe(step["timeout"])
            if rc is None:
                self.term.key("C-c")
                self.probe(10)
                return dict(res, status="FAIL", output=self.term.since(mark),
                            seconds=round(time.time() - t0, 1),
                            reason="hung: no prompt after {}s (sent ^C) in command {} of {}: {}".format(
                                step["timeout"], i + 1, len(cmds), short(cmd, 60)))
            rcs.append(rc)
            if rc and not step.get("expect_fail"):
                return dict(res, status="FAIL", rc=rcs, output=self.term.since(mark),
                            seconds=round(time.time() - t0, 1),
                            reason="exit code {} in command {} of {}: {}".format(
                                rc, i + 1, len(cmds), short(cmd, 60)))
        out = self.term.since(mark)
        res.update(rc=rcs, output=out, seconds=round(time.time() - t0, 1))
        if step.get("expect_fail"):
            if any(rcs):
                return dict(res, status="PASS", reason="failed as expected (exit code {})".format(
                    [r for r in rcs if r][-1]))
            return dict(res, status="FAIL", reason="expected a failure, but every exit code was 0")
        m = ERRORISH.search(clean(out))
        return dict(res, status="PASS", reason="",
                    warn="output has {!r}".format(m.group(0)) if m else "")

    def wait_for(self, text, mark, timeout):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if text in self.term.since(mark):
                return True
            time.sleep(0.5)
        return False

    def run_other(self, step):
        res = dict(id=step["id"], file=step["file"], line=step["line"], title=step["title"],
                   command="{} {}".format(step["method"], step["data"]).strip(), mode=step["method"])
        method, data = step["method"], step["data"]
        if method == "key" or (method == "keys" and KEYISH.match(data)):
            self.term.key(data)
            self.term.settle()
        elif method == "keys":
            self.term.type(data, enter=False)
            self.term.settle()
        elif method == "tmux":
            self.term.tmux(*shlex.split(data))
            self.term.settle(maximum=3)
        elif method in ("wait", "longwait"):
            timeout = LONGWAIT_TIMEOUT if method == "longwait" else WAIT_TIMEOUT
            if not self.wait_for(data, self.group_mark, timeout):
                return dict(res, status="FAIL", reason="{!r} not shown after {}s".format(data, timeout),
                            output=self.term.since(self.group_mark))
        elif method in ("copy", "copypaste"):
            matches = re.findall(data, self.term.since(self.group_mark), re.DOTALL)
            if not matches:
                return dict(res, status="FAIL", reason="regex {!r} not found".format(data),
                            output=self.term.since(self.group_mark))
            self.clipboard = matches[-1].replace("\n", "")
            if method == "copypaste":
                self.term.type(self.clipboard, enter=False)
        elif method == "paste":
            self.term.type(self.clipboard, enter=False)
        elif method == "open":
            if "xxx" in data:
                return dict(res, status="SKIP", reason="URL has a placeholder", output="")
            r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-m", "10", "-w", "%{http_code}",
                                data], capture_output=True, text=True)
            code = r.stdout.strip()
            ok = code[:1] in ("2", "3")
            return dict(res, status="PASS", reason="HTTP {}".format(code),
                        warn="" if ok else "URL check got HTTP {}".format(code or "no answer"), output="")
        else:
            return dict(res, status="SKIP", reason="unknown method {!r}".format(method), output="")
        return dict(res, status="PASS", reason="", output="", screen=self.term.screen())

    def write_log(self, step, res, output):
        path = os.path.join(self.rundir, "steps", "{:04d}.log".format(step["id"]))
        with open(path, "w") as f:
            f.write("# step {id} {status}  {file}:{line}  \"{title}\"\n".format(**res))
            f.write("# mode={} seconds={} rc={}\n".format(res.get("mode"), res.get("seconds"), res.get("rc")))
            if res.get("reason"):
                f.write("# reason: {}\n".format(res["reason"]))
            if res.get("warn"):
                f.write("# warning: {}\n".format(res["warn"]))
            f.write("# command:\n{}\n# output:\n{}\n".format(res["command"], clean(output)))
            if res.get("screen"):
                f.write("# screen after the step:\n{}\n".format(clean(res["screen"])))
            if res.get("diagnostics"):
                f.write("# diagnostics:\n{}\n".format(res["diagnostics"]))

    def report(self, step, res):
        flag = res["status"] + ("*" if res.get("warn") else "")
        self.progress.write("{:<5} {:>4} {}:{} {}{}\n".format(
            flag, step["id"], step["file"], step["line"], short(res["command"], 70),
            "  ← " + res["reason"] if res["status"] == "FAIL" else ""))

    def run(self):
        self.term.start()
        self.progress.write("START {} steps\n".format(len(self.plan["steps"])))
        for step in self.plan["steps"]:
            if step["method"] in ("bash", "hide"):
                res = self.run_command(step)
            else:
                res = self.run_other(step)
            if res["status"] == "FAIL":
                try:
                    res["diagnostics"] = self.diagnostics()
                except Exception as e:  # Diagnostics must never stop the run.
                    res["diagnostics"] = "diagnostics failed: {}".format(e)
            self.write_log(step, res, res.get("output", ""))
            res.pop("screen", None)
            res["output_tail"] = clean(res.pop("output", ""))[-3000:]
            self.results.append(res)
            self.report(step, res)
            if res["status"] == "FAIL" and self.plan.get("stop_on_fail"):
                break
        self.ensure_prompt()
        json.dump(self.results, open(os.path.join(self.rundir, "results.json"), "w"), indent=1)
        self.write_summary()
        self.progress.write("DONE\n")

    def write_summary(self):
        r = self.results
        count = {k: sum(1 for x in r if x["status"] == k) for k in ("PASS", "FAIL", "SKIP")}
        warns = [x for x in r if x.get("warn") and x["status"] == "PASS"]
        lines = ["# Lab test: {}".format(self.plan["deck"]), "",
                 "{} steps: {PASS} pass, {FAIL} fail, {SKIP} skip, {w} pass with warning. "
                 "Total {s:.0f}s.".format(len(r), w=len(warns),
                                           s=sum(x.get("seconds") or 0 for x in r), **count), ""]
        fails = [x for x in r if x["status"] == "FAIL"]
        if fails:
            lines += ["## Failures (the first one can cause the others)", ""]
            for x in fails:
                tail = "\n".join(x["output_tail"].split("\n")[-20:])
                lines += ["### step {id} — {file}:{line} — {title}".format(**x),
                          "Reason: {}".format(x["reason"]), "", "```",
                          tail, "```", "Full log: steps/{:04d}.log".format(x["id"]), ""]
        if warns:
            lines += ["## Passed, but the output looks like an error (check it)", ""]
            lines += ["- step {id} {file}:{line} — {warn}: `{cmd}`".format(
                cmd=short(x["command"], 60), **x) for x in warns]
            lines.append("")
        skips = [x for x in r if x["status"] == "SKIP"]
        if skips:
            lines += ["## Skipped", ""]
            lines += ["- step {id} {file}:{line} — {reason}".format(**x) for x in skips]
            lines.append("")
        lines += ["## Time per file", ""]
        per_file = {}
        for x in r:
            per_file[x["file"]] = per_file.get(x["file"], 0) + (x.get("seconds") or 0)
        lines += ["- {}: {:.0f}s".format(f, s) for f, s in per_file.items()]
        open(os.path.join(self.rundir, "summary.md"), "w").write("\n".join(lines) + "\n")


def cmd_exec(args):
    Runner(args.rundir).run()


# ----------------------------------------------------------------- run ---

class Lab:
    def __init__(self, tag, cluster):
        tagdir = os.path.join(REPO, "prepare-labs", "tags", tag)
        if not os.path.isdir(tagdir):
            sys.exit("No lab tag {!r} in prepare-labs/tags/.".format(tag))
        rows = [l.split() for l in open(os.path.join(tagdir, "clusters.tsv")) if l.strip()]
        self.ip = rows[cluster - 1][0]
        self.key = os.path.join(tagdir, "id_rsa")
        self.user = "k8s"
        for line in open(os.path.join(tagdir, "settings.env")):
            m = re.match(r"^USER_LOGIN=(\S+)", line)
            if m:
                self.user = m.group(1)

    def ssh(self, command, stdin=None, check=True, stream=False):
        argv = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
                "-o", "LogLevel=ERROR", "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
                "-o", "ServerAliveInterval=15", "-i", self.key, "ubuntu@" + self.ip,
                "sudo -iu {} bash -c {}".format(self.user, shlex.quote(command))]
        if stream:
            return subprocess.Popen(argv, stdout=subprocess.PIPE, text=True)
        r = subprocess.run(argv, input=stdin, capture_output=True,
                           text=not isinstance(stdin, bytes))
        if check and r.returncode:
            sys.exit("ssh failed ({}): {}".format(r.returncode, r.stderr))
        return r.stdout


def follow(lab, runid):
    """Show progress lines until DONE. Return True when the run is done."""
    proc = lab.ssh("tail -n +1 -F {}/runs/{}/progress.log 2>/dev/null".format(REMOTE_DIR, runid),
                   stream=True)
    done = False
    try:
        for line in proc.stdout:
            print(line, end="", flush=True)
            if line.strip() == "DONE":
                done = True
                break
    except KeyboardInterrupt:
        print("\nStopped following. The run continues on the node. "
              "Use: labtest.py attach --tag TAG {}".format(runid))
    finally:
        proc.terminate()
    return done


def fetch(lab, runid):
    local = os.path.join(HERE, "runs", runid)
    os.makedirs(os.path.dirname(local), exist_ok=True)
    data = lab.ssh("tar -C {}/runs -cz {}".format(REMOTE_DIR, runid), stdin=b"")
    r = subprocess.run(["tar", "-xz", "-C", os.path.join(HERE, "runs")], input=data)
    if r.returncode:
        sys.exit("Could not extract the results.")
    latest = os.path.join(HERE, "runs", "latest")
    if os.path.islink(latest) or os.path.exists(latest):
        os.remove(latest)
    os.symlink(runid, latest)
    print("\nResults: {}".format(os.path.relpath(local, os.getcwd())))
    print(open(os.path.join(local, "summary.md")).read())


def cmd_run(args):
    plan = make_plan(args.deck, args.only, args.start, args.stop)
    plan["stop_on_fail"] = args.stop_on_fail
    if not plan["steps"]:
        sys.exit("No steps selected.")
    lab = Lab(args.tag, args.cluster)
    busy = lab.ssh("pgrep -u $(id -u) -f '[l]abtest.py exec' || true").strip()
    if busy:
        sys.exit("A lab test already runs on {} (pid {}). Stop it: labtest.py stop --tag {}".format(
            lab.ip, busy, args.tag))
    runid = time.strftime("%Y%m%d-%H%M%S")
    rdir = "{}/runs/{}".format(REMOTE_DIR, runid)
    lab.ssh("mkdir -p {} && cat > {}/labtest.py".format(rdir, REMOTE_DIR),
            stdin=open(__file__).read())
    lab.ssh("cat > {}/plan.json".format(rdir), stdin=json.dumps(plan))
    lab.ssh("cd {d} && setsid nohup python3 labtest.py exec runs/{r} > runs/{r}/exec.log 2>&1 < /dev/null &"
            .format(d=REMOTE_DIR, r=runid))
    print("Run {} on {}@{}: {} steps. Watch it live: labtest.py watch --tag {}".format(
        runid, lab.user, lab.ip, len(plan["steps"]), args.tag))
    if follow(lab, runid):
        fetch(lab, runid)


def cmd_attach(args):
    lab = Lab(args.tag, args.cluster)
    if follow(lab, args.runid):
        fetch(lab, args.runid)


def cmd_stop(args):
    lab = Lab(args.tag, args.cluster)
    lab.ssh("pkill -u $(id -u) -f '[l]abtest.py exec'; tmux -L labtest kill-server", check=False)
    print("Stopped.")


def cmd_watch(args):
    lab = Lab(args.tag, args.cluster)
    os.execvp("ssh", ["ssh", "-t", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
                      "-o", "LogLevel=ERROR", "-o", "IdentitiesOnly=yes", "-i", lab.key,
                      "ubuntu@" + lab.ip, "sudo -iu {} tmux -L labtest attach -r -t lt".format(lab.user)])


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    def selection(sp):
        sp.add_argument("deck", help="deck manifest, e.g. kube-sec-twodays.yml")
        sp.add_argument("--only", action="append", default=[],
                        help="only this Markdown file (repeat for more), e.g. k8s/daemonset.md")
        sp.add_argument("--from", dest="start", help="start at FILE or FILE:LINE")
        sp.add_argument("--to", dest="stop", help="stop after FILE")

    def target(sp):
        sp.add_argument("--tag", required=True, help="lab tag in prepare-labs/tags/")
        sp.add_argument("--cluster", type=int, default=1, help="cluster number (default 1)")

    sp = sub.add_parser("plan", help="list the steps of a deck (no lab needed)")
    selection(sp)
    sp.add_argument("-v", "--verbose", action="store_true", help="list every step")
    sp.add_argument("-o", "--output", help="also write the plan as JSON")
    sp.set_defaults(func=cmd_plan)

    sp = sub.add_parser("run", help="run the steps on node1 of a lab")
    selection(sp)
    target(sp)
    sp.add_argument("--stop-on-fail", action="store_true", help="stop at the first failure")
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("attach", help="follow a run again, then download its results")
    target(sp)
    sp.add_argument("runid")
    sp.set_defaults(func=cmd_attach)

    sp = sub.add_parser("watch", help="watch the test terminal live (read-only tmux)")
    target(sp)
    sp.set_defaults(func=cmd_watch)

    sp = sub.add_parser("stop", help="stop a run")
    target(sp)
    sp.set_defaults(func=cmd_stop)

    sp = sub.add_parser("exec", help="(on the node) run a plan")
    sp.add_argument("rundir")
    sp.set_defaults(func=cmd_exec)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
