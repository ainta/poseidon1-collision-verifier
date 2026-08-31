# Poseidon1 Collision Reproduction

## Collision

This repository reproduces the full-round collision described in [*Midpoint Reset: A Full-Round Poseidon Collision from an Adaptively Chosen MDS Matrix*](https://eprint.iacr.org/2026/1760).

`solution.json` contains two distinct 15-element inputs, `X` and `Y`, and an MDS matrix `M` chosen after the round constants were fixed for the Poseidon1 compression instance:

- field: `p = 2130706433`
- S-box: `x³`
- state width: `16`
- rounds: `RF = 8`, `RP = 20`
- fixed prefix: `0xc09de4`

Using the [Poseidon Initiative](https://www.poseidon-initiative.info/)'s verifier, both inputs produce the same complete 16-coordinate output:

```text
[12623332, 381610402, 1098917770, 1214689931,
 1088609520, 1417244378, 389562611, 528440087,
 1037009343, 103050012, 1856868908, 844069,
 2047831014, 2081742232, 501746317, 1636319921]
```

Verification is pinned to the Poseidon Initiative's [`khovratovich/poseidon-tools`](https://github.com/khovratovich/poseidon-tools) commit `60075da7c0521d9493749a035b1f30d4eda37138`. `verify.py` fetches that commit and calls its `verify_collision_solution` function directly; it contains no alternative Poseidon implementation.

## Run

Requirements: Python 3.9 or later, Git, and internet access.

```bash
git clone https://github.com/ainta/poseidon1-collision-verifier.git
cd poseidon1-collision-verifier
python3 verify.py
```

Successful verification ends with:

```text
official_t16 True
```
