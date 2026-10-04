# Lab tests

`labtest.py` runs the commands of every `.lab[]` block of a deck on a lab
cluster, in deck order, and tells you which commands fail and why. It types
each command into a tmux session on node1, as the student user, like a
student does. It needs no install: it uses the Python 3 standard library on
your computer and on the node.

## Commands

Run these from the `slides/` directory.

```bash
make labtest-plan DECK=kube-sec-twodays.yml
```

Lists the commands of the deck per file, without a lab. It also lists the
commands that will probably hang (`watch`, `vim`, `logs -f`, ...) because no
directive after them tells the test what to do.

```bash
make labtest DECK=kube-sec-twodays.yml TAG=bret
```

Runs the full deck on node1 of lab `TAG` (a directory in
`prepare-labs/tags/`). Progress shows one line per step. When the run is
done, the results go to `labtest/runs/<run-id>/` (`labtest/runs/latest`
points to the last run), and the summary shows on screen.

Select part of a deck:

```bash
make labtest TAG=bret ONLY="k8s/daemonset.md k8s/rollout.md"
```

```bash
make labtest TAG=bret FROM=k8s/daemonset.md TO=k8s/rollout.md
```

`FROM` also accepts `file:line`, for example `FROM=k8s/daemonset.md:500`.

```bash
make labtest-watch TAG=bret
```

Shows the test terminal live (read-only tmux). Press Ctrl-B then D to leave.

```bash
make labtest-stop TAG=bret
```

Stops a run. If your computer loses the connection during a run, the run
continues on the node. Use `python3 labtest/labtest.py attach --tag bret
<run-id>` to follow it again.

## Results

- `summary.md`: counts, then each failure with its file:line, slide title,
  reason, and the last 20 lines of output. Read this first.
- `steps/NNNN.log`: the full output of each step, the screen after
  interactive steps, and for failures, the pods that do not run and the last
  cluster events.
- `progress.log`: one line per step. `results.json`: all data.

Status values:

- `PASS`: the exit code is 0, or the `wait` text showed.
- `PASS*`: passed, but the output contains a word like "error" or
  "forbidden". Check it. Some lab output is correct with these words.
- `FAIL`: wrong exit code, `wait` text not shown, or no prompt before the
  timeout (the test sends Ctrl-C and continues).
- `SKIP`: a `skip` directive.

The first failure can cause the next ones, because each chapter uses the
state of the chapters before it. On a lab that you already used, a chapter
can fail because of old state (for example, a deployment that exists). For a
full dry run, use a fresh lab.

## Directives

A directive is a one-line code block in a `.lab[]` block. Put it in an HTML
comment, so students do not see it. Most directives apply to the command
block just before them.

````markdown
- Check the logs:
  ```bash
  kubectl logs deploy/pingpong --follow
  ```

<!--
```wait seq=```
```key ^C```
-->
````

| Directive | What it does |
|---|---|
| `wait TEXT` | Do not wait for the prompt. Pass when TEXT shows (60 s). |
| `longwait TEXT` | Same as `wait`, but 600 s. |
| `key KEY` | Send one key: `^C`, `^D`, `^[` (Escape), `^J`, `Enter`, `Space`. |
| `keys TEXT` | Type TEXT, with no Enter. |
| `tmux ARGS` | Run a tmux command, for example `tmux split-pane -v`. |
| `hide COMMAND` | Run a command that students do not see. |
| `copy REGEX` / `paste` / `copypaste REGEX` | Copy text from the output, then type it. |
| `open URL` | Check the URL with curl from node1. Gives a warning only. |
| `expect-fail` | The command must fail. Use it when a slide shows an error on purpose. |
| `timeout SECONDS` | Time limit for the command (default 120 s). |
| `skip REASON` | Do not run the command. Report it as SKIP. |

Interactive programs (vim, k9s, `kubectl edit`, `logs -f`, `watch`): put
`wait`, `keys`, and `key` directives after the command, to do what the
student does. vim accepts `^J` as Enter. k9s and other full-screen programs
need `key Enter`. If the program still runs before the next command, the
step fails with "program still running", and the test sends Ctrl-C, Escape,
and `:q!` to recover.

Nested shells work: `ssh node2`, `kubectl exec -it ... -- sh`, and `exit`.

## How it works

1. `plan` reads the deck manifest (the `content:` list and `exclude:`
   classes), then each Markdown file. It keeps the code blocks in `.lab[]`
   blocks, with their file and line. It ignores slides with an excluded
   class, speaker notes, and `yaml`/`json` blocks (students read these).
2. `run` copies `labtest.py` and the plan to `~/.labtest/` of the student
   user on node1, and starts `labtest.py exec` there in the background. Thus
   a lost connection does not stop the run.
3. `exec` starts a private tmux server (`tmux -L labtest`), so it does not
   touch other tmux sessions. After each command, it types
   `echo __LTRC_$?_$((0+N))`. When `__LTRC_<rc>_<N>` shows, the command is
   done and `<rc>` is its exit code. Lines with `__LTRC_` are removed from
   the logs.
