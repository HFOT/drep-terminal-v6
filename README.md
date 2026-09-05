# DRep Governance Terminal

Read Cardano's DRep landscape from numbers you can verify.

**→ https://hfot.github.io/drep-terminal-v6/**

English by default, with a Japanese toggle (`JA` / `EN` in the top-right).

## What this page is for

It shows the **structure of voting power** — who holds how much, and how concentrated
that is. It opens on the aggregate view rather than an empty screen.

- Total voting power, active DRep count, governance participation rate
- **Nakamoto coefficient** — how many DReps it takes to control 51% (lower = more concentrated)
- Top 1 / 5 / 10 / 20 concentration, with the denominator spelled out
- Delegator mix (share held by large holders), delegation flow, VP stability
- Top DRep list → click through to an individual view (VP history, delegator mix, flow log)

There is **no delegation simulator**. This is a place to read; actual delegation belongs
in a wallet (Eternl / Lace) or GovTool.

## Data

Everything comes from [Koios](https://koios.rest/), using only free endpoints that need no API key.
`drep-snapshot.json` is rebuilt by GitHub Actions **once a day** and the page reads that
same-origin file. The page also shows its own source panel: which API, which endpoints,
which epoch, and when it was fetched.

**Why not call Koios directly from the browser:** Koios does not return an
`Access-Control-Allow-Origin` header on actual GET responses, so a page on static hosting
always fails CORS. (The preflight *does* pass, which makes this easy to misdiagnose.)

### Accuracy notes

- **All active DReps are fetched**, not a top-N slice. Taking only the top 50 made the
  concentration denominator too small and overstated every percentage.
- The denominator is **named DReps**, not the raw epoch total. At epoch 652 the total
  delegated to DReps was 15,061 M₳, but `drep_always_abstain` alone held 9,777 M₳ (65%)
  and `drep_always_no_confidence` 150 M₳. Those are predefined options, not representatives,
  so they are reported separately and excluded from the denominator. The page shows this
  breakdown so the number is checkable.
- Koios returns history at **epoch granularity** (1 epoch = 5 days), so a true 24-hour
  change is not obtainable. The page shows **change vs. previous epoch** and labels it that way.
- Delegator counts come from `live_delegator_count` in `drep_info`.
- `name_ja` (Japanese labels) and `category` are **not on-chain**. They are curated by hand
  in `tools/drep-curated.json` and carried across rebuilds by DRep ID. DReps without an entry
  show their English metadata name and an "unknown" category.

## Layout

| | |
|---|---|
| `index.html` | The page. Opens standalone too — it then falls back to embedded data |
| `drep-snapshot.json` | Daily snapshot (written by Actions) |
| `tools/build-drep-snapshot.py` | Generator. Standard library only, no pip install |
| `tools/check-drep-snapshot.py` | Guards against committing an empty or gutted snapshot |
| `tools/drep-curated.json` | Hand-maintained Japanese labels and categories |
| `.github/workflows/drep-snapshot.yml` | Daily at 21:10 UTC (06:10 JST), plus manual dispatch |

Rebuild locally:

```bash
DREP_OUT=drep-snapshot.json python tools/build-drep-snapshot.py
DREP_OUT=drep-snapshot.json python tools/check-drep-snapshot.py
```

Useful environment variables: `DREP_TOP_N` (0 = all active DReps, the default),
`DREP_EPOCH_WINDOW` (epochs of history, default 75), `DREP_OUT`, `DREP_PAUSE`.

## Disclaimer

These figures are on-chain data aggregated as-is. They are not investment advice and not a
recommendation of any DRep. Use them as material for your own judgement.
