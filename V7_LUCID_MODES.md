# TAURUS V7 – two parallel books (not deployed)

## Product confirmed 2026-10-26
Base checkout **LucidFlex 25K Evaluation**, the smallest Flex size. Its cheapest checkout option is **Daily Loss Limit ON + 40% consistency**. Lucid says DLL ON must be enforced in both evaluation and funded. The 25K account has profit target $1,250, EOD trailing Max Loss Limit $1,000, and max 2 minis / 20 micros in evaluation. Funded scaling initially allows 1 mini / 10 micros; later sizing updates at end of session. Check live purchase screen and actual DLL dollar amount before enabling a strict comparison.

References:
- https://support.lucidtrading.com/en/articles/16226050-lucidflex-customization
- https://support.lucidtrading.com/en/articles/12945790-lucidflex-evaluation-account
- https://support.lucidtrading.com/en/articles/12945808-lucidflex-scaling-plan
- https://support.lucidtrading.com/en/articles/12945815-lucidflex-drawdown

## Modes
1. **LAB_RESEARCH**: keep ALL strategies, winners, losers, and zero-trade scanners. No account-level loss cap, no daily stop, and continue observing after -$1,000. Report gross and net results by strategy, score, time segment, market. Never claim this is an eligible Lucid account.
2. **LUCID_SHADOW**: pass the very same signals into a shared 25K account with max contracts, consistent net direction per instrument, Lucid MLL, configured DLL, end-of-day cutoff, commission/slippage and account qualification. On MLL breach mark **FAILED** and stop its simulation; LAB_RESEARCH keeps collecting trades. Do not quietly reset failed simulated accounts or treat post-breach positions as Lucid-compliant.

Research mode has NO extra loss limits. The Lucid shadow account must obey actual Lucid rules or it is not a valid assessment. Limit adjustments only after final choice of strategies must NOT be conflated with a real historical Lucid result.

## Current implementation status
- lucid_25k_sim.py: isolated strict account admission/size and EOD skeleton
- v7_parallel_research.py: independent unlimited research log and Lucid shadow signal admission, **not yet a full two-book execution engine**
- Existing V6 still running on main; do not merge/deploy this branch.
- Needed: exact DLL parameter from Lucid checkout, persist DB externally, mark-to-market enforcement, forced daily flatten, trading sessions/calendar, proper multiple-position execution and close attribution, fee and tick data, stream and replay validation, CI tests. No real trades.
