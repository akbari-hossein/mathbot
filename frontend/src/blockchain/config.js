// Where the contract lives. By default the values come from the backend
// (GET /api/contract/config/), so nothing has to be rebuilt when the contract is redeployed.
// They can be overridden with REACT_APP_CHAIN_ID + REACT_APP_CONTEST_CONTRACT_ADDRESS.
import axiosConfig from '../utils/config.js';
import { WalletError } from './errors.js';

let cached = null;

function fromEnv() {
    const chainId = process.env.REACT_APP_CHAIN_ID;
    const contractAddress = process.env.REACT_APP_CONTEST_CONTRACT_ADDRESS;
    if (!chainId || !contractAddress) {
        return null;
    }
    return {
        configured: true,
        chainId: Number(chainId),
        contractAddress,
        explorerUrl: process.env.REACT_APP_BLOCKCHAIN_EXPLORER_URL || '',
    };
}

/**
 * Chain id + contract address (cached for the session).
 * @throws {WalletError} blockchain_not_configured - the backend has no contract configured yet
 */
export async function getContractConfig({ force = false } = {}) {
    if (cached && !force) {
        return cached;
    }
    const env = fromEnv();
    if (env) {
        cached = env;
        return cached;
    }
    let data;
    try {
        ({ data } = await axiosConfig().get('/contract/config/'));
    } catch (error) {
        throw new WalletError('network_error');
    }
    if (!data?.configured || !data?.contract_address) {
        throw new WalletError('blockchain_not_configured');
    }
    cached = {
        configured: true,
        chainId: Number(data.chain_id),
        contractAddress: data.contract_address,
        explorerUrl: data.explorer_url || '',
    };
    return cached;
}

/** On-chain state of a contest, read through the backend (works without a wallet). */
export async function fetchContestFromBackend(contestId) {
    try {
        const { data } = await axiosConfig().get(`/contract/contests/${contestId}/`);
        return data;
    } catch (error) {
        if (error?.response?.status === 404) {
            return null; // contest is not on the contract (yet)
        }
        throw error;
    }
}

export function explorerTxUrl(explorerUrl, txHash) {
    return explorerUrl ? `${explorerUrl.replace(/\/$/, '')}/tx/${txHash}` : null;
}

export function resetContractConfigCache() {
    cached = null;
}
