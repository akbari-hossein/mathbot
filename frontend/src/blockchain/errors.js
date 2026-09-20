// Turns wallet / contract errors into a Persian message you can show the user.
// The contract messages are the same list as backend/contractapi/errors.py - keep them in sync.

export const CONTRACT_ERROR_MESSAGES = {
    ContestAlreadyExists: 'این مسابقه قبلا در قرارداد هوشمند ثبت شده است.',
    ContestNotFound: 'این مسابقه هنوز روی قرارداد هوشمند ثبت نشده است.',
    ContestNotActive: 'این مسابقه تمام یا لغو شده است.',
    ContestStillActive: 'این مسابقه هنوز تمام نشده است.',
    ContestNotCancelled: 'این مسابقه لغو نشده است.',
    InvalidDeadline: 'مهلت ثبت نام باید در آینده باشد.',
    SignupClosed: 'مهلت ثبت نام این مسابقه تمام شده است.',
    IncorrectPayment: 'مبلغ پرداختی با هزینه ثبت نام برابر نیست.',
    InvalidUserRef: 'شناسه کاربری نامعتبر است، دوباره وارد حساب خود شوید.',
    AlreadyRegistered: 'با این کیف پول قبلا در این مسابقه ثبت نام کرده‌اید.',
    NotRegistered: 'با این کیف پول در این مسابقه ثبت نام نکرده‌اید یا مبلغ آن قبلا بازگردانده شده است.',
    ZeroValue: 'مبلغ باید بیشتر از صفر باشد.',
    InvalidAddress: 'آدرس کیف پول نامعتبر است.',
    DuplicateWinner: 'یک آدرس نمی‌تواند چند رتبه را بگیرد.',
    LengthMismatch: 'تعداد برندگان و جوایز برابر نیست.',
    InvalidPercentage: 'مجموع درصدها نباید بیشتر از ۱۰۰ باشد.',
    InsufficientContestBalance: 'موجودی این مسابقه برای پرداخت جوایز کافی نیست.',
    NothingToWithdraw: 'مبلغی برای برداشت وجود ندارد.',
    TransferFailed: 'ارسال اتر ناموفق بود.',
    RenounceOwnershipDisabled: 'این عملیات غیرفعال است.',
    OwnableUnauthorizedAccount: 'این عملیات فقط از طرف مالک قرارداد امکان‌پذیر است.',
    OwnableInvalidOwner: 'آدرس مالک نامعتبر است.',
    EnforcedPause: 'قرارداد هوشمند موقتا متوقف شده است، بعدا دوباره تلاش کنید.',
    ExpectedPause: 'قرارداد هوشمند متوقف نیست.',
    ReentrancyGuardReentrantCall: 'درخواست همزمان تکراری رد شد.',
};

export const WALLET_ERROR_MESSAGES = {
    wallet_missing: 'کیف پول متامسک پیدا نشد. برای پرداخت، افزونه متامسک را نصب کنید.',
    not_connected: 'ابتدا کیف پول خود را وصل کنید.',
    user_rejected: 'شما درخواست را در کیف پول لغو کردید.',
    request_pending: 'یک درخواست دیگر در متامسک باز است، ابتدا آن را ببندید.',
    wrong_network: 'شبکه کیف پول درست نیست.',
    insufficient_funds: 'موجودی کیف پول شما برای این پرداخت و کارمزد کافی نیست.',
    blockchain_not_configured: 'پرداخت با رمزارز هنوز فعال نشده است.',
    network_error: 'ارتباط با شبکه بلاکچین برقرار نشد، کمی بعد دوباره تلاش کنید.',
    unknown: 'خطای ناشناخته در ارتباط با کیف پول.',
};

export class WalletError extends Error {
    constructor(code, message) {
        super(message || WALLET_ERROR_MESSAGES[code] || WALLET_ERROR_MESSAGES.unknown);
        this.name = 'WalletError';
        this.code = code;
    }
}

function rejected(error) {
    const codes = [error?.code, error?.info?.error?.code, error?.error?.code, error?.cause?.code];
    return codes.includes(4001) || codes.includes('ACTION_REJECTED');
}

/**
 * Normalises anything thrown by ethers / MetaMask / this module.
 * @returns {{code: string, message: string, args: object|null, original: any}}
 */
export function toFriendlyError(error) {
    const done = (code, message, args = null) => ({
        code,
        message: message || WALLET_ERROR_MESSAGES[code] || WALLET_ERROR_MESSAGES.unknown,
        args,
        original: error,
    });

    if (error instanceof WalletError) {
        return done(error.code, error.message);
    }
    if (rejected(error)) {
        return done('user_rejected');
    }
    if (error?.code === -32002) {
        return done('request_pending');
    }
    // custom error of ContestPrize.sol, decoded by ethers from the ABI
    const revert = error?.revert || error?.info?.error?.revert;
    if (revert?.name) {
        const args = revert.args ? Object.fromEntries(revert.args.map((value, i) => [i, String(value)])) : null;
        return done(revert.name, CONTRACT_ERROR_MESSAGES[revert.name], args);
    }
    if (error?.code === 'INSUFFICIENT_FUNDS' || /insufficient funds/i.test(error?.message || '')) {
        return done('insufficient_funds');
    }
    if (error?.code === 'NETWORK_ERROR' || error?.code === 'TIMEOUT' || error?.code === 'ERR_NETWORK') {
        return done('network_error');
    }
    return done('unknown', error?.shortMessage || error?.message);
}
