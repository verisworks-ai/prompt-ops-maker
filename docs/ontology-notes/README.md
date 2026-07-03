# Ontology notes

Prompt Ops Maker models a small service graph:

```text
CLI surfaces
  - prompt-ops-maker list-projects
  - prompt-ops-maker list-types
  - prompt-ops-maker make
  - prompt-ops-maker make-adhoc

Artifacts
  - project YAML configs
  - generic type presets
  - generated prompt markdown

Safety gates
  - no secret output
  - no unapproved deploy/upload/database/account-setting change
  - evidence-first report
  - unverified-item report
```
