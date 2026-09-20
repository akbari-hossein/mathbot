// Everything the UI needs to do with the ContestPrize contract: read a contest, pay the
// signup fee, claim a refund. Every function throws errors you can pass to toFriendlyError().
import { Contract, formatEther, getAddress } from 'ethers';
import { jwtDecode } from 'jwt-decode';

import ABI from './ContestPrize.abi.json';
import { getContractConfig } from './config.js';
import { WalletError } from './errors.js';
import { connectWallet, ensureNetwork, getConnectedAccount, getProvider, getSigner } from './wallet.js';

/** Backend user id from the JWT in localStorage - the contract stores it with the signup. */
export function currentUserId() {
    try {
        const token = localStorage.getItem('token');
        const userId = token ? jwtDecode(token).user_id : null;
        return userId ? Number(userId) : null;
    } catch (error) {
        return null;
    }
}

async function readContract() {
    const { contractAddress } = await getContractConfig();
    return new Contract(contractAddress, ABI, getProvider());
}

async function writeContract() {
    const { contractAddress } = await getContractConfig();
    return new Contract(contractAddress, ABI, await getSigner());
}

function shapeContest(contestId, raw) {
    const state = raw.status ? 'active' : raw.cancelled ? 'cancelled' : 'finished';
    return {
        contestId: Number(contestId),
        state,
        priceWei: raw.Price,
        priceEth: formatEther(raw.Price),
        isFree: raw.Price === 0n,
        totalWei: raw.Total_amount,
        totalEth: formatEther(raw.Total_amount),
        participants: Number(raw.participants),
        signupDeadline: new Date(Number(raw.signupDeadline) * 1000),
    };
}

/** Reads a contest straight from the chain (needs a wallet). Returns null if it does not exist. */
export async function getContestOnChain(contestId) {
    const contract = await readContract();
    if (!(await contract.getcompexist(contestId))) {
        return null;
    }
    const [raw, signupOpen] = await Promise.all([contract.getcomp(contestId), contract.isSignupOpen(contestId)]);
    return { ...shapeContest(contestId, raw), signupOpen };
}

export async function isRegistered(contestId, address) {
    const contract = await readContract();
    return contract.isRegistered(contestId, getAddress(address));
}

/**
 * Pays the signup fee of a contest. Connects the wallet and switches to the right network first.
 *
 *   const { tx, wallet } = await signupForContest({ contestId });
 *   await tx.wait();                       // 1 confirmation
 *   await api.post(`/contests/${contestId}/signup/`, { wallet_address: wallet, tx_hash: tx.hash });
 *
 * @returns {Promise<{tx: import('ethers').TransactionResponse, wallet: string, priceWei: bigint}>}
 */
export async function signupForContest({ contestId, userId = null }) {
    const ref = userId != null ? Number(userId) : currentUserId();
    if (!ref) {
        throw new WalletError('unknown', 'برای ثبت نام ابتدا وارد حساب کاربری خود شوید.');
    }
    const { chainId } = await getContractConfig();
    const { address } = await connectWallet();
    await ensureNetwork(chainId);

    const contract = await writeContract();
    if (!(await contract.getcompexist(contestId))) {
        throw new WalletError('ContestNotFound', 'این مسابقه هنوز روی قرارداد هوشمند ثبت نشده است.');
    }
    if (await contract.isRegistered(contestId, address)) {
        throw new WalletError('AlreadyRegistered', 'با این کیف پول قبلا در این مسابقه ثبت نام کرده‌اید.');
    }
    if (!(await contract.isSignupOpen(contestId))) {
        throw new WalletError('SignupClosed', 'مهلت ثبت نام این مسابقه تمام شده است.');
    }

    // the price comes from the contract itself, never from the UI
    const { Price: priceWei } = await contract.getcomp(contestId);
    const tx = await contract.signup(contestId, ref, { value: priceWei });
    return { tx, wallet: address, priceWei };
}

/** Takes the entry fee back from a cancelled contest. @returns {Promise<import('ethers').TransactionResponse>} */
export async function claimRefund(contestId) {
    const { chainId } = await getContractConfig();
    const { address } = await connectWallet();
    await ensureNetwork(chainId);

    const contract = await writeContract();
    if (!(await contract.isRegistered(contestId, address))) {
        throw new WalletError('NotRegistered', 'با این کیف پول در این مسابقه ثبت نام نکرده‌اید یا مبلغ آن بازگردانده شده است.');
    }
    return contract.claimRefund(contestId);
}

/** True when the connected wallet already paid for this contest (no popup). */
export async function hasPaidForContest(contestId) {
    const address = await getConnectedAccount();
    return address ? isRegistered(contestId, address) : false;
}
