/**
 * @jest-environment node
 *
 * The chain part runs only when a node + a deployed contract are given, e.g.
 *
 *   anvil
 *   cd contracts/Contest_prize && forge script script/ContestPrize.s.sol:Deploycontestprize \
 *        --rpc-url http://127.0.0.1:8545 --broadcast
 *   REACT_APP_TEST_RPC_URL=http://127.0.0.1:8545 REACT_APP_CHAIN_ID=31337 \
 *   REACT_APP_CONTEST_CONTRACT_ADDRESS=0x... REACT_APP_TEST_OWNER_KEY=0x... REACT_APP_TEST_USER_KEY=0x... \
 *   npm test -- --watchAll=false --testPathPattern blockchain
 *
 * `window.ethereum` is replaced by a small EIP-1193 object that forwards to the node,
 * so this really exercises signing, paying and the contract calls.
 */
// The config comes from REACT_APP_* here, so the backend (axios) must not be touched at all.
// Mocking it also keeps jest away from the ESM build of axios.
jest.mock('../utils/config.js', () => ({
    __esModule: true,
    default: () => ({
        get: () => {
            throw new Error('the backend should not be called when REACT_APP_CONTEST_CONTRACT_ADDRESS is set');
        },
    }),
}));

const { JsonRpcProvider, Wallet, Contract, NonceManager, parseEther } = require('ethers');

const ABI = require('./ContestPrize.abi.json');
const { toFriendlyError, WalletError, CONTRACT_ERROR_MESSAGES } = require('./errors.js');
const { networkLabel, toHexChainId } = require('./networks.js');

const RPC_URL = process.env.REACT_APP_TEST_RPC_URL;
const CONTRACT = process.env.REACT_APP_CONTEST_CONTRACT_ADDRESS;
const OWNER_KEY = process.env.REACT_APP_TEST_OWNER_KEY;
const USER_KEY = process.env.REACT_APP_TEST_USER_KEY;
const USER_ID = 77;

// ----------------------------------------------------------------------
// unit tests (no chain)
// ----------------------------------------------------------------------

describe('error mapping', () => {
    it('detects a user rejection in both shapes', () => {
        expect(toFriendlyError({ code: 4001 }).code).toBe('user_rejected');
        expect(toFriendlyError({ code: 'ACTION_REJECTED' }).code).toBe('user_rejected');
        expect(toFriendlyError({ info: { error: { code: 4001 } } }).code).toBe('user_rejected');
    });

    it('maps a contract error to its Persian message', () => {
        const friendly = toFriendlyError({ revert: { name: 'SignupClosed', args: [5] } });
        expect(friendly.code).toBe('SignupClosed');
        expect(friendly.message).toBe(CONTRACT_ERROR_MESSAGES.SignupClosed);
    });

    it('keeps WalletError codes and falls back for unknown errors', () => {
        expect(toFriendlyError(new WalletError('wallet_missing')).code).toBe('wallet_missing');
        expect(toFriendlyError({ code: -32002 }).code).toBe('request_pending');
        expect(toFriendlyError({ code: 'INSUFFICIENT_FUNDS' }).code).toBe('insufficient_funds');
        expect(toFriendlyError(new Error('boom')).message).toBe('boom');
    });

    it('has a message for every contract error in the ABI', () => {
        const names = ABI.filter((item) => item.type === 'error').map((item) => item.name);
        expect(names.filter((name) => !CONTRACT_ERROR_MESSAGES[name])).toEqual([]);
    });
});

describe('networks', () => {
    it('formats chain ids and labels', () => {
        expect(toHexChainId(11155111)).toBe('0xaa36a7');
        expect(networkLabel(11155111)).toContain('Sepolia');
        expect(networkLabel(4242)).toBe('شبکه 4242');
    });
});

describe('without a wallet', () => {
    it('hasWallet is false and signup fails with a clear message', async () => {
        delete global.window;
        jest.resetModules();
        const { hasWallet } = require('./wallet.js');
        expect(hasWallet()).toBe(false);
        const { signupForContest } = require('./contestPrize.js');
        global.localStorage = { getItem: () => null };
        await expect(signupForContest({ contestId: 1, userId: 5 })).rejects.toMatchObject({
            code: 'wallet_missing',
        });
    });
});

// ----------------------------------------------------------------------
// against a real node
// ----------------------------------------------------------------------

const chainIt = RPC_URL && CONTRACT && OWNER_KEY && USER_KEY ? describe : describe.skip;

chainIt('signup flow on a real chain', () => {
    let provider;
    let owner;
    let ownerContract;  // owner = the backend wallet in production
    let blockchain;
    let userAddress;

    // minimal MetaMask: sends everything to the node, signs with USER_KEY
    function installFakeWallet(signer, address, chainId) {
        const ethereum = {
            isMetaMask: true,
            currentChainId: toHexChainId(chainId),
            async request({ method, params = [] }) {
                switch (method) {
                    case 'eth_requestAccounts':
                    case 'eth_accounts':
                        return [address];
                    case 'eth_chainId':
                        return this.currentChainId;
                    case 'wallet_switchEthereumChain':
                        this.currentChainId = params[0].chainId;
                        return null;
                    case 'eth_sendTransaction': {
                        const [tx] = params;
                        const sent = await signer.sendTransaction({
                            to: tx.to,
                            data: tx.data,
                            value: tx.value ?? 0,
                            from: undefined,
                        });
                        return sent.hash;
                    }
                    default:
                        return provider.send(method, params);
                }
            },
            on() {},
            removeListener() {},
        };
        global.window = { ethereum };
        return ethereum;
    }

    beforeAll(async () => {
        // cacheTimeout: -1 -> no cached nonces, MetaMask keeps track of them itself
        provider = new JsonRpcProvider(RPC_URL, undefined, { cacheTimeout: -1, batchMaxCount: 1 });
        owner = new NonceManager(new Wallet(OWNER_KEY, provider));
        ownerContract = new Contract(CONTRACT, ABI, owner);
        const userWallet = new Wallet(USER_KEY, provider);
        userAddress = userWallet.address;
        installFakeWallet(new NonceManager(userWallet), userAddress, Number(process.env.REACT_APP_CHAIN_ID));
        global.localStorage = { getItem: (key) => (key === 'token' ? null : null) };
        jest.resetModules();
        blockchain = require('./index.js');
    });

    async function createContest(priceEth, { budgetEth = '0', seconds = 86400 } = {}) {
        const id = Math.floor(Math.random() * 1e9);
        const deadline = (await provider.getBlock('latest')).timestamp + seconds;
        const tx = await ownerContract.Addcomp(id, parseEther(priceEth), deadline, {
            value: parseEther(budgetEth),
        });
        await tx.wait();
        return id;
    }

    it('reads a contest from the chain', async () => {
        const id = await createContest('0.02');
        const contest = await blockchain.getContestOnChain(id);
        expect(contest).toMatchObject({
            contestId: id,
            state: 'active',
            priceEth: '0.02',
            isFree: false,
            participants: 0,
            signupOpen: true,
        });
        expect(contest.signupDeadline.getTime()).toBeGreaterThan(Date.now());
        expect(await blockchain.getContestOnChain(999999999)).toBeNull();
    });

    it('pays the entry fee and registers the user id', async () => {
        const id = await createContest('0.02');
        expect(await blockchain.hasPaidForContest(id)).toBe(false);

        const { tx, wallet, priceWei } = await blockchain.signupForContest({ contestId: id, userId: USER_ID });
        const receipt = await tx.wait();

        expect(receipt.status).toBe(1);
        expect(wallet).toBe(userAddress);
        expect(priceWei).toBe(parseEther('0.02'));
        expect(await blockchain.isRegistered(id, userAddress)).toBe(true);
        expect(await blockchain.hasPaidForContest(id)).toBe(true);
        // the contract stored the backend user id, this is what the backend verifies
        expect(await ownerContract.getParticipantRef(id, userAddress)).toBe(BigInt(USER_ID));
        const contest = await blockchain.getContestOnChain(id);
        expect([contest.participants, contest.totalEth]).toEqual([1, '0.02']);
    });

    it('refuses a second signup with the same wallet', async () => {
        const id = await createContest('0.01');
        await (await blockchain.signupForContest({ contestId: id, userId: USER_ID })).tx.wait();
        await expect(blockchain.signupForContest({ contestId: id, userId: USER_ID })).rejects.toMatchObject({
            code: 'AlreadyRegistered',
        });
    });

    it('refuses signup after the deadline', async () => {
        const id = await createContest('0.01', { seconds: 120 });
        await provider.send('evm_increaseTime', [3600]);
        await provider.send('evm_mine', []);
        await expect(blockchain.signupForContest({ contestId: id, userId: USER_ID })).rejects.toMatchObject({
            code: 'SignupClosed',
        });
    });

    it('refuses signup for a contest that is not on the contract', async () => {
        await expect(blockchain.signupForContest({ contestId: 888888888, userId: USER_ID })).rejects.toMatchObject({
            code: 'ContestNotFound',
        });
    });

    it('needs a logged in user', async () => {
        const id = await createContest('0.01');
        await expect(blockchain.signupForContest({ contestId: id })).rejects.toMatchObject({ code: 'unknown' });
    });

    it('claims the refund of a cancelled contest', async () => {
        const id = await createContest('0.5');
        await (await blockchain.signupForContest({ contestId: id, userId: USER_ID })).tx.wait();
        await (await ownerContract.cancelComp(id)).wait();

        const before = await provider.getBalance(userAddress);
        const refund = await blockchain.claimRefund(id);
        const receipt = await refund.wait();
        const after = await provider.getBalance(userAddress);

        const gas = receipt.gasUsed * receipt.gasPrice;
        expect(after - before + gas).toBe(parseEther('0.5'));
        expect(await blockchain.isRegistered(id, userAddress)).toBe(false);
        await expect(blockchain.claimRefund(id)).rejects.toMatchObject({ code: 'NotRegistered' });
    });

    it('takes the user id from the JWT when it is not passed', async () => {
        const token = [
            Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url'),
            Buffer.from(JSON.stringify({ user_id: 4242, username: 'player' })).toString('base64url'),
            'signature',
        ].join('.');
        global.localStorage = { getItem: (key) => (key === 'token' ? token : null) };
        jest.resetModules();
        const fresh = require('./index.js');
        expect(fresh.currentUserId()).toBe(4242);

        const id = await createContest('0.01');
        await (await fresh.signupForContest({ contestId: id })).tx.wait();
        expect(await ownerContract.getParticipantRef(id, userAddress)).toBe(4242n);
    });

    it('switches the wallet to the configured network', async () => {
        global.window.ethereum.currentChainId = '0x1';
        const id = await createContest('0.01');
        await (await blockchain.signupForContest({ contestId: id, userId: USER_ID })).tx.wait();
        expect(global.window.ethereum.currentChainId).toBe(toHexChainId(Number(process.env.REACT_APP_CHAIN_ID)));
    });
});
