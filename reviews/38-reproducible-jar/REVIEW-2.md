Finding 1 is closed. The group now separates workflows and PR numbers: same-named fork branches cannot cancel each other or a `main` push. Cancellation remains possible for runs on the same ref. [GitHub concurrency documentation](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)

The push filter introduces no new coverage gap for changes reaching `main`: matching PR changes still trigger validation; merges and direct pushes touching `mod/**` trigger validation afterward. Branches without PRs now wait until reaching `main`. This does **not** guarantee successful testing before merge; existing path-filter limitations and same-ref cancellation still apply. [Workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)

YAML parsing succeeded. Fork PR triggers remain correct, subject to GitHub’s normal approval requirements. `workflow_dispatch` remains independent of push filters and supports selecting another ref, subject to default-branch availability. [Event documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)

Read-only; no builds run.

SAFE