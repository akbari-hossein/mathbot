// MetaMask (EIP-1193) helpers: connect, read the current account, switch network, listen to changes.
import { BrowserProvider, getAddress } from 'ethers';

import { WalletError } from './errors.js';
import { NETWORKS, networkLabel, toHexChainId } from './networks.js';

export function hasWallet() {
    return typeof window !== 'undefined' && Boolean(window.ethereum);
}

function ethereum() {
    if (!hasWallet()) {
        throw new WalletError('wallet_missing');
    }
    return window.ethereum;
}

/** ethers provider over MetaMask ('any' = follow network changes instead of throwing). */
export function getProvider() {
    return new BrowserProvider(ethereum(), 'any');
}

export async function getSigner() {
    return getProvider().getSigner();
}

/** Address of the already connected account, or null. Never opens a popup. */
export async function getConnectedAccount() {
    if (!hasWallet()) {
        return null;
    }
    const accounts = await ethereum().request({ method: 'eth_accounts' });
    return accounts && accounts.length ? getAddress(accounts[0]) : null;
}

/** Asks the user to connect (opens MetaMask). @returns {Promise<{address: string, chainId: number}>} */
export async function connectWallet() {
    const accounts = await ethereum().request({ method: 'eth_requestAccounts' });
    if (!accounts || !accounts.length) {
        throw new WalletError('not_connected');
    }
    return { address: getAddress(accounts[0]), chainId: await getChainId() };
}

export async function getChainId() {
    return Number(await ethereum().request({ method: 'eth_chainId' }));
}

/** Makes sure the wallet is on `chainId`, asking it to switch (or add the network) if needed. */
export async function ensureNetwork(chainId) {
    const wanted = Number(chainId);
    if ((await getChainId()) === wanted) {
        return;
    }
    try {
        await ethereum().request({
            method: 'wallet_switchEthereumChain',
            params: [{ chainId: toHexChainId(wanted) }],
        });
    } catch (error) {
        const unknownNetwork = error?.code === 4902 || error?.data?.originalError?.code === 4902;
        if (unknownNetwork && NETWORKS[wanted]) {
            await ethereum().request({ method: 'wallet_addEthereumChain', params: [NETWORKS[wanted]] });
        } else {
            throw error;
        }
    }
    if ((await getChainId()) !== wanted) {
        throw new WalletError('wrong_network', `لطفا در کیف پول خود به ${networkLabel(wanted)} تغییر دهید.`);
    }
}

function subscribe(event, handler) {
    if (!hasWallet()) {
        return () => {};
    }
    window.ethereum.on(event, handler);
    return () => window.ethereum.removeListener(event, handler);
}

/** @param {(address: string|null) => void} callback @returns {() => void} unsubscribe */
export function onAccountsChanged(callback) {
    return subscribe('accountsChanged', (accounts) =>
        callback(accounts && accounts.length ? getAddress(accounts[0]) : null)
    );
}

/** @param {(chainId: number) => void} callback @returns {() => void} unsubscribe */
export function onChainChanged(callback) {
    return subscribe('chainChanged', (chainId) => callback(Number(chainId)));
}

/** 0x1234...abcd - for showing an address in the UI. */
export function shortAddress(address) {
    return address ? `${address.slice(0, 6)}...${address.slice(-4)}` : '';
}
