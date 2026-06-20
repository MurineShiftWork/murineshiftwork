# Tutorial 7: Reading session files

## Prerequisites

[Tutorial 6: Managing subjects](06_subject_management.md), and at least one
session on disk (Tutorial 2 produced one).

## What you'll learn

- Which files a session writes and what each one is for.
- How to load a session in Python with the bundled readers.
- What the format version field means for reading old data.

## 1. The files a session writes

Every session writes a small, fixed set of files into its acquisition directory.
The names share a `.msw.` infix so they are easy to find and unambiguous:

| File | Contents |
|---|---|
| `<basename>.msw.session.yaml` | session metadata: format version, task, subject, setup, and the resolved settings |
| `<basename>.msw.df.jsonl` | trial-by-trial data: one JSON record per line |
| `<basename>.msw.log` | human-readable run log |
| `<basename>.msw.plot_spec.yaml` | the task's plot specification (see [Tutorial 8](08_plot_spec.md)) |

The `<basename>` encodes the identity of the run as
`subject__datetime__task`, so a file is self-describing even out of context.

## 2. The session metadata file

`*.msw.session.yaml` is the human-readable record of what ran. Its first field is
the one that matters most for durability:

```yaml
msw_format_version: 2
process:
  task: sequence
  subject: mouse001
  setup: rig-a
  session_basename: mouse001__20260526_100149_223167__sequence
task_settings:
  start_level: 7
  stop_trials: 500
```

`msw_format_version` records the on-disk layout the session was written with.
Readers use it to interpret older files correctly, so a session written years
ago still loads. You do not have to track versions yourself: the readers do it.

## 3. The trial data file

`*.msw.df.jsonl` is line-delimited JSON. The first line is a version header; each
later line is one trial:

```json
{"_msw_version": "1.0"}
{"trial_index": 0, "outcome": "correct", "reward_ul": 3.0, ...}
{"trial_index": 1, "outcome": "incorrect", "reward_ul": 0.0, ...}
```

The exact trial fields are defined by the task, not the framework, so they vary
between protocols. Treat the JSONL as the source of truth for what happened on
each trial.

## 4. Load a session in Python

Rather than parse these files by hand, use the bundled reader API. It returns a
structured object with the metadata and the trial data already loaded into a
pandas DataFrame:

```python
from murineshiftwork.readers import load_session

session = load_session(
    "/home/you/data/mouse001/"
    "mouse001__20260526_100149_223167__session__sequence/"
    "mouse001__20260526_100149_223167__sequence"
)

print(session.subject)        # 'mouse001'
print(session.task)           # 'sequence'
print(session.msw_version)    # software version that wrote it
print(session.df.head())      # trial-by-trial DataFrame
print(session.settings_task)  # the resolved task settings as a dict
```

The readers handle format detection for you: `session.is_complete` tells you
whether all expected artifacts were present, and the reader transparently loads
older on-disk formats.

## 5. Load many sessions at once

To load every session for one animal, point `load_subject` at the subject's data
directory:

```python
from murineshiftwork.readers import load_subject

sessions = load_subject("/home/you/data/mouse001")
for s in sessions:
    print(s.basename, len(s.df) if s.df is not None else 0, "trials")
```

`load_acquisition` does the same for a single acquisition container (useful for
multi-protocol sessions). All three return the same session object type, so your
analysis code does not branch on how the data was grouped.

## You now know

A session writes a fixed set of `.msw.` files, with `msw_format_version`
guaranteeing old data stays readable. The `murineshiftwork.readers` API loads
one session, one acquisition, or a whole subject into a uniform structured object
with a pandas DataFrame, so you can start analysis without parsing files by hand.

## Next

[Tutorial 8: The plot spec](08_plot_spec.md). For the full file layout and reader
return fields, see [Session Files](../concepts/session_files.md).
