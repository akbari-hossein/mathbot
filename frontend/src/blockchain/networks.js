// Network metadata, used to ask the wallet to switch (or add) the right network.
// The keys are chain ids. Sepolia (11155111) is the test network we use.

export const NETWORKS = {
    1: {
        chainId: '0x1',
        chainName: 'Ethereum Mainnet',
        nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
        rpcUrls: ['https://ethereum-rpc.publicnode.com'],
        blockExplorerUrls: ['https://etherscan.io'],
    },
    11155111: {
        chainId: '0xaa36a7',
        chainName: 'Sepolia',
        nativeCurrency: { name: 'Sepolia Ether', symbol: 'ETH', decimals: 18 },
        rpcUrls: ['https://ethereum-sepolia-rpc.publicnode.com'],
        blockExplorerUrls: ['https://sepolia.etherscan.io'],
    },
    31337: {
        chainId: '0x7a69',
        chainName: 'Anvil (local)',
        nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
        rpcUrls: ['http://127.0.0.1:8545'],
        blockExplorerUrls: [],
    },
};

// Persian names shown in the UI ("لطفا به شبکه ... تغییر دهید")
export const NETWORK_LABELS = {
    1: 'اتریوم',
    11155111: 'تست‌نت Sepolia',
    31337: 'شبکه محلی',
};

export function networkLabel(chainId) {
    return NETWORK_LABELS[Number(chainId)] || `شبکه ${chainId}`;
}

export function toHexChainId(chainId) {
    return `0x${Number(chainId).toString(16)}`;
}
