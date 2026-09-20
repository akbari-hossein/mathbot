// React hook with the wallet state the UI needs. No styling, no markup - build the button yourself.
//
//   const { hasWallet, address, connect, isCorrectNetwork, switchNetwork, error } = useWallet();
//
import { useCallback, useEffect, useState } from 'react';

import { getContractConfig } from './config.js';
import { toFriendlyError } from './errors.js';
import { networkLabel } from './networks.js';
import {
    connectWallet,
    getChainId,
    getConnectedAccount,
    hasWallet,
    onAccountsChanged,
    onChainChanged,
    ensureNetwork,
    shortAddress,
} from './wallet.js';

export default function useWallet() {
    const [address, setAddress] = useState(null);
    const [chainId, setChainId] = useState(null);
    const [config, setConfig] = useState(null);
    const [connecting, setConnecting] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        let alive = true;

        getContractConfig()
            .then((value) => alive && setConfig(value))
            .catch((err) => alive && setError(toFriendlyError(err)));

        if (hasWallet()) {
            getConnectedAccount().then((value) => alive && setAddress(value));
            getChainId().then((value) => alive && setChainId(value));
        }

        const unsubscribeAccounts = onAccountsChanged(setAddress);
        const unsubscribeChain = onChainChanged(setChainId);
        return () => {
            alive = false;
            unsubscribeAccounts();
            unsubscribeChain();
        };
    }, []);

    const connect = useCallback(async () => {
        setConnecting(true);
        setError(null);
        try {
            const wallet = await connectWallet();
            setAddress(wallet.address);
            setChainId(wallet.chainId);
            return wallet.address;
        } catch (err) {
            setError(toFriendlyError(err));
            return null;
        } finally {
            setConnecting(false);
        }
    }, []);

    const switchNetwork = useCallback(async () => {
        setError(null);
        try {
            const target = config ? config.chainId : (await getContractConfig()).chainId;
            await ensureNetwork(target);
            setChainId(await getChainId());
            return true;
        } catch (err) {
            setError(toFriendlyError(err));
            return false;
        }
    }, [config]);

    const expectedChainId = config ? config.chainId : null;
    return {
        hasWallet: hasWallet(),
        address,
        shortAddress: shortAddress(address),
        chainId,
        expectedChainId,
        expectedNetworkLabel: expectedChainId ? networkLabel(expectedChainId) : '',
        isCorrectNetwork: Boolean(expectedChainId) && chainId === expectedChainId,
        isConfigured: Boolean(config),
        explorerUrl: config ? config.explorerUrl : '',
        connecting,
        error,
        clearError: () => setError(null),
        connect,
        switchNetwork,
    };
}
