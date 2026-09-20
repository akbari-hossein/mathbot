# Blockchain integration (ContestPrize)

The blockchain layer (contract + the code that connects to it) is written and tested. This document
says **what the backend and the frontend developer have to do**.

- Contract: `contracts/Contest_prize/` · Backend: `backend/contractapi/` · Frontend: `frontend/src/blockchain/`
- The contract only holds money; all contest logic stays in Django. **A contest id on the contract is
  the `id` of its `Contest` row in the database.**

| Who | What |
|---|---|
| Backend / server owner | **Deploying the contract and creating the server wallet** (see "Deployment"), the model changes and the payment check |
| Frontend owner | The UI for connecting a wallet and signing up |

Deploying is deliberately the job of whoever runs the server: the owner private key stays on that
machine, so the person who manages it has to create and keep it.

## How it works

```
admin → POST /api/contract/admin/contests/         → contract: the contest is created
user  → MetaMask: signup(contestId, userId) + pays the entry fee
      → POST /api/contests/<id>/signup/ {wallet_address, tx_hash}
        backend checks the payment with verify_signup() → Participation is created
admin → POST .../award/top3/ (or another award type) → prizes are sent to the winners
```

When a user pays, the transaction also carries their backend user id. The contract stores it, so the
backend can be sure this wallet really paid **for that user** - nobody can claim somebody else's
transaction as their own.

## Local setup

```bash
anvil                                            # local test chain (separate terminal)
cd contracts/Contest_prize && forge build
PRIVATE_KEY=<anvil-key-0> forge script script/ContestPrize.s.sol:Deploycontestprize \
  --rpc-url http://127.0.0.1:8545 --broadcast     # prints the contract address
```

Put the address in `backend/.env` (all variables are in `backend/.env.example`):

```env
BLOCKCHAIN_RPC_URL=http://127.0.0.1:8545
BLOCKCHAIN_CHAIN_ID=31337
CONTEST_CONTRACT_ADDRESS=0x...
BLOCKCHAIN_OWNER_PRIVATE_KEY=<anvil-key-0>
```

If these are empty the rest of the site works normally and only the blockchain endpoints answer `503`.

---

## Deployment to the testnet (backend / server owner)

> Do this with **your own wallet**: the owner private key lives on the server and can move all the
> contest money, so the person who runs the server has to create it and keep it.

**1) Create a wallet for the server** - a **new** account in MetaMask (not your personal wallet) and
copy its private key (Account details → Show private key).

**2) Get test ETH:** switch to Sepolia and send about 0.5 test ETH to that address from a faucet
(e.g. `sepoliafaucet.com` or the Google Cloud faucet). It pays the gas and the prize budget of free
contests.

**3) Get an RPC url:** create a free project on Infura or Alchemy and copy its Sepolia url.

**4) Contract env file:**

```bash
cd contracts/Contest_prize
cp .env.example .env      # fill in SEPOLIA_RPC_URL and PRIVATE_KEY (the server wallet key)
```

Safer (optional): instead of writing the key into a file, run `cast wallet import deployer --interactive`
and add `--account deployer` to the command below.

**5) Deploy:**

```bash
forge build
forge script script/ContestPrize.s.sol:Deploycontestprize --rpc-url sepolia --broadcast --verify
```

Copy the `ContestPrize deployed at: 0x...` line from the output. (`--verify` needs `ETHERSCAN_API_KEY`;
without it the deploy still works, only the source is not published on the explorer.)
To deploy from a different wallet but leave ownership with the server wallet, set
`CONTRACT_OWNER=<server wallet address>` in `.env` before running it.

**6) Configure the backend** (`backend/.env`) and restart the server:

```env
BLOCKCHAIN_RPC_URL=<the RPC url from step 3>
BLOCKCHAIN_CHAIN_ID=11155111
CONTEST_CONTRACT_ADDRESS=<the address from step 5>
BLOCKCHAIN_OWNER_PRIVATE_KEY=<the server wallet key>
BLOCKCHAIN_EXPLORER_URL=https://sepolia.etherscan.io
```

**7) Smoke test:**

```bash
curl -H "Authorization: Bearer <admin-jwt>" http://localhost:8000/api/contract/admin/owner/
# must return server_wallet_is_owner: true and a non-zero balance
```

Then create a test contest, sign up with another wallet, award the prizes and withdraw the site share.

**Keeping it safe:**

- The private key belongs in `backend/.env` only - not in git, not in a chat, not in a screenshot.
  If it leaks: `POST /api/contract/admin/pause/`, move the money out with `withdrawOwner`, and deploy
  again with a new wallet.
- Keep a small balance on the server wallet and move the site share to a cold wallet regularly.
- Every redeploy means a new address; contests created on the old contract stay there, so settle their
  prizes and withdrawals before switching.
- Mainnet needs an independent security review first.

---

## Backend

**1) Models** (`contests/models.py`):

```python
class Contest(models.Model):
    price = models.DecimalField(max_digits=30, decimal_places=18, default=0)   # currently a TextField
    chain_tx_hash = models.CharField(max_length=66, blank=True, default='')

class Participation(models.Model):
    wallet_address = models.CharField(max_length=42, blank=True, default='')   # the prize goes here
    signup_tx_hash = models.CharField(max_length=66, blank=True, default='')
```

**2) Register the contest on the contract** after it is created in the database:

```python
from contractapi import services

tx = services.create_contest(
    contest.id, price_eth=contest.price, signup_deadline=contest.start_time, user=request.user
)
contest.chain_tx_hash = tx.tx_hash
```

**3) Check the payment in `ContestSignupAPIView`** (the important part - before creating the `Participation`):

```python
from contractapi import services
from contractapi.errors import BlockchainError

wallet = (request.data.get('wallet_address') or '').strip()
tx_hash = request.data.get('tx_hash')
try:
    on_chain = services.get_contest(contest.id)          # None = not registered on the contract
    if on_chain and not on_chain['is_free']:
        if not wallet or not services.verify_signup(contest.id, wallet, request.user.id, tx_hash=tx_hash):
            return Response({'error': 'payment_not_found', 'detail': 'پرداخت شما روی بلاکچین پیدا نشد.'}, status=400)
except BlockchainError as exc:
    return Response(exc.as_dict(), status=exc.http_status)

Participation.objects.create(contest=contest, user=request.user,
                             wallet_address=wallet, signup_tx_hash=tx_hash or '')
```

Never trust what the frontend claims about a payment; `verify_signup` reads it from the contract.

**4) The other service functions** (each returns a `ContractTransaction`):

```python
services.cancel_contest(id, user=...)               services.refund_participants(id, wallets, user=...)
services.award_top3(id, a, b, c, user=...)          services.award_with_percentage(id, a, b, c, [50,30,10], user=...)
services.award_fixed(id, a, b, c, ['0.5','0.3','0.1'], user=...)
services.award_duel(id, winner, user=...)           services.award_custom(id, winners, amounts, user=...)
services.withdraw_owner_share(id, treasury, user=...)   # the site share after the contest ends
```

**5) Existing bugs in the `contests` app that need fixing:**

- `ContestsCreateAPIView` has no `serializer_class`, so `POST /api/contests/create/` already returns 500;
  its permission should also be `IsAdminUser` (right now any user can create a contest).
- `ContestsDeleteAPIView` uses `IsOwnerOrAdmin`, which checks `obj.creator`, but the model field is `created_by`.
- `migrations/` is in `.gitignore` and the container runs `makemigrations` on startup - risky in production.
- `DEBUG = True` and `ALLOWED_HOSTS = ["*"]` are hardcoded; `CommonMiddleware` is listed twice and
  `CorsMiddleware` has to come before it.
- The `backend` service in `docker-compose.yml` has no `env_file`.

---

## Frontend

`ethers` is installed and all the logic lives in `src/blockchain/`; only the UI is left. The contract
settings are loaded from `GET /api/contract/config/` automatically, so no env variable is needed.

**Connect wallet button:**

```jsx
import { useWallet, shortAddress } from '../blockchain';

const w = useWallet();
if (!w.hasWallet)        return <a href="https://metamask.io/download/">نصب متامسک</a>;
if (!w.address)          return <button onClick={w.connect}>{w.connecting ? '...' : 'اتصال کیف پول'}</button>;
if (!w.isCorrectNetwork) return <button onClick={w.switchNetwork}>تغییر شبکه به {w.expectedNetworkLabel}</button>;
return <span>{shortAddress(w.address)}</span>;
```

**Signing up for a contest:**

```jsx
import { signupForContest, toFriendlyError } from '../blockchain';
import config from '../utils/config.js';

try {
    setStep('کیف پول را تایید کنید');
    const { tx, wallet } = await signupForContest({ contestId: contest.id });

    setStep('در حال تایید تراکنش...');          // takes a few seconds
    await tx.wait();

    setStep('در حال ثبت نهایی...');
    await config().post(`/contests/${contest.id}/signup/`, { wallet_address: wallet, tx_hash: tx.hash });
} catch (err) {
    setError(toFriendlyError(err).message);      // ready made Persian message
}
```

Other functions: `claimRefund(contestId)` for a cancelled contest, `fetchContestFromBackend(contestId)`
to show the on-chain state without a wallet, and `hasPaidForContest(contestId)`.

**Notes:**

- Never set the amount in the UI; `signupForContest` reads the price from the contract itself.
- If the user closes the page in the middle, the money is paid but the signup is not finished. Pressing
  the button again gives an `AlreadyRegistered` error - in that case just send the backend request again.
- `screens/Contest.js` is still a static placeholder and has to load the contest from `/api/contests/<id>/`.
- Existing bug: `utils/api.js` reads `process.env.SERVER_APP_API_URL`, but CRA only injects variables
  prefixed with `REACT_APP_`, so production always falls back to `localhost:8000`. Rename it to
  `REACT_APP_API_URL`.

---

## Backend API (under `/api/contract/`)

| Method | Path | Access |
|---|---|---|
| GET | `config/` | public |
| GET | `contests/<id>/` | public - on-chain state of a contest |
| GET | `contests/<id>/participants/<wallet>/` | logged in user |
| POST | `admin/contests/` | admin - `contest_id`, `price_eth`, `signup_deadline`, `budget_eth?` |
| POST | `admin/contests/<id>/{deadline,budget,cancel,refund,withdraw}/` | admin |
| POST | `admin/contests/<id>/award/{top3,percentage,fixed,duel,custom}/` | admin |
| POST | `admin/{pause,unpause}/` · GET `admin/owner/` | admin |
| GET | `admin/transactions/` and `admin/transactions/<tx_hash>/` | admin |

A `202` response means the transaction was **sent**, not mined: `{"tx_hash", "status": "pending", "explorer_url"}`.
Poll `admin/transactions/<tx_hash>/` for the final status.
Errors are always `{"error": "<code>", "detail": "<Persian message>"}` and the codes are the same on the
backend and the frontend (`ContestNotFound`, `SignupClosed`, `AlreadyRegistered`,
`InsufficientContestBalance`, `EnforcedPause`, ...). Full list: `backend/contractapi/errors.py` and
`frontend/src/blockchain/errors.js`. Interactive docs: `/swagger/` with an admin account.

---

## Security

- The money endpoints are admin only (`is_staff`); every transaction is logged in the
  `ContractTransaction` table and visible in the Django admin.
- Watch the balance of the server wallet (`GET /api/contract/admin/owner/`) - an empty wallet means
  awarding prizes fails.
- In an emergency `POST /api/contract/admin/pause/` stops every money operation.
- The rest of the key / wallet notes are in the "Deployment" section.

## Tests

```bash
cd contracts/Contest_prize && forge test                                   # 50 contract tests
cd backend && BLOCKCHAIN_TEST_RPC_URL=http://127.0.0.1:8545 python manage.py test contractapi
cd frontend && npm test -- --watchAll=false --testPathPattern blockchain   # needs anvil, see the test file header
```

After any change to `ContestPrize.sol`, run `bash script/export-abi.sh` and commit the result
(CI fails when the ABI is out of date).
