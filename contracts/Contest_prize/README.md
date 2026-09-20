# ContestPrize

Smart contract for the MathBot contests: it holds the entry fees and the prize budget of every
contest and pays the winners. A contest id on the contract is **the `id` of its `Contest` row in the
Django database**.

Full integration guide for the backend and the frontend:
[`docs/blockchain-integration.md`](../../docs/blockchain-integration.md)

## Layout

```
src/ContestPrize.sol                the contract
test/ContestPrize.t.sol             unit + fuzz tests
test/ContestPrize.invariant.t.sol   invariant test (balance accounting)
script/ContestPrize.s.sol           deployment
script/export-abi.sh                writes the ABI for the backend and the frontend
```

## Build and test

```bash
forge build --sizes
forge test -vvv
forge coverage --no-match-coverage '\.t\.sol|\.s\.sol'
forge fmt            # CI checks this with forge fmt --check
```

Dependencies: `lib/forge-std` is a submodule, so after cloning run

```bash
git submodule update --init --recursive
```

## Deployment

```bash
cp .env.example .env     # fill in SEPOLIA_RPC_URL and PRIVATE_KEY
forge script script/ContestPrize.s.sol:Deploycontestprize --rpc-url sepolia --broadcast --verify
```

- Instead of `PRIVATE_KEY` you can use an encrypted keystore:
  `cast wallet import deployer --interactive` and then `--account deployer`.
- If `CONTRACT_OWNER` is set, ownership is transferred to that address (the backend wallet) right
  after the deploy.

After deploying:

1. Put the contract address in `backend/.env` → `CONTEST_CONTRACT_ADDRESS`.
2. If the contract changed, run `bash script/export-abi.sh` and commit the generated files.

## Notes

- **The owner is the backend wallet.** Creating a contest, awarding prizes, cancelling, refunding and
  withdrawing are owner-only.
- Each contest keeps its own money: the sum of all `Total_amount` values always equals the contract
  balance (the invariant test checks exactly this).
- Besides taking the payment, `signup(id, userRef)` stores the backend user id, so the backend can tie
  a payment to the account that made it.
- Sending ETH directly to the contract is rejected (there is no `receive` function), so money cannot
  be lost without a signup.
- `renounceOwnership` is disabled - otherwise the contest money would be locked forever.
- In an emergency `pause()` stops every money operation.

The public function names (`Addcomp`, `Awardwinners`, ...) are kept as they were, so the backend and
the frontend do not have to change.
