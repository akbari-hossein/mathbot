// Blockchain layer of MathBot (ContestPrize contract).
// Read docs/blockchain-integration.md before using it.
export { default as useWallet } from './useWallet.js';
export {
    claimRefund,
    currentUserId,
    getContestOnChain,
    hasPaidForContest,
    isRegistered,
    signupForContest,
} from './contestPrize.js';
export { explorerTxUrl, fetchContestFromBackend, getContractConfig } from './config.js';
export {
    connectWallet,
    ensureNetwork,
    getChainId,
    getConnectedAccount,
    hasWallet,
    onAccountsChanged,
    onChainChanged,
    shortAddress,
} from './wallet.js';
export { CONTRACT_ERROR_MESSAGES, WALLET_ERROR_MESSAGES, WalletError, toFriendlyError } from './errors.js';
export { NETWORKS, networkLabel } from './networks.js';
