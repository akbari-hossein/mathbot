"""Errors of the blockchain layer. `code` is stable (for the frontend), `message` is shown to users."""

# Persian messages for the custom errors of ContestPrize.sol and the OpenZeppelin errors it inherits.
# frontend/src/blockchain/errors.js has the same list - keep them in sync.
CONTRACT_ERROR_MESSAGES = {
    'ContestAlreadyExists': 'مسابقه‌ای با این شناسه قبلا در قرارداد هوشمند ثبت شده است.',
    'ContestNotFound': 'این مسابقه در قرارداد هوشمند ثبت نشده است.',
    'ContestNotActive': 'این مسابقه تمام یا لغو شده است.',
    'ContestStillActive': 'این مسابقه هنوز تمام نشده است.',
    'ContestNotCancelled': 'این مسابقه لغو نشده است.',
    'InvalidDeadline': 'مهلت ثبت نام باید در آینده باشد.',
    'SignupClosed': 'مهلت ثبت نام این مسابقه تمام شده است.',
    'IncorrectPayment': 'مبلغ پرداختی با هزینه ثبت نام برابر نیست.',
    'InvalidUserRef': 'شناسه کاربر نامعتبر است.',
    'AlreadyRegistered': 'این کیف پول قبلا در این مسابقه ثبت نام کرده است.',
    'NotRegistered': 'این کیف پول در این مسابقه ثبت نام نکرده یا مبلغ آن قبلا بازگردانده شده است.',
    'ZeroValue': 'مبلغ باید بیشتر از صفر باشد.',
    'InvalidAddress': 'آدرس کیف پول نامعتبر است.',
    'DuplicateWinner': 'یک آدرس نمی‌تواند چند رتبه را بگیرد.',
    'LengthMismatch': 'تعداد برندگان و جوایز برابر نیست.',
    'InvalidPercentage': 'مجموع درصدها نباید بیشتر از ۱۰۰ باشد.',
    'InsufficientContestBalance': 'موجودی این مسابقه برای پرداخت این جوایز کافی نیست.',
    'NothingToWithdraw': 'مبلغی برای برداشت وجود ندارد.',
    'TransferFailed': 'ارسال اتر به یکی از آدرس‌ها ناموفق بود (آدرس مقصد اتر را قبول نمی‌کند).',
    'RenounceOwnershipDisabled': 'این عملیات غیرفعال است.',
    'OwnableUnauthorizedAccount': 'کیف پول سرور مالک قرارداد هوشمند نیست.',
    'OwnableInvalidOwner': 'آدرس مالک نامعتبر است.',
    'EnforcedPause': 'قرارداد هوشمند به طور موقت متوقف شده است.',
    'ExpectedPause': 'قرارداد هوشمند متوقف نیست.',
    'ReentrancyGuardReentrantCall': 'درخواست همزمان تکراری رد شد.',
}


class BlockchainError(Exception):
    code = 'blockchain_error'
    http_status = 502
    default_message = 'خطا در ارتباط با بلاکچین.'

    def __init__(self, message=None, code=None, details=None):
        self.message = message or self.default_message
        if code:
            self.code = code
        self.details = details or {}
        super().__init__(self.message)

    def as_dict(self):
        data = {'error': self.code, 'detail': self.message}
        if self.details:
            data['details'] = self.details
        return data


class BlockchainNotConfigured(BlockchainError):
    code = 'blockchain_not_configured'
    http_status = 503
    default_message = 'اتصال به قرارداد هوشمند تنظیم نشده است.'


class BlockchainUnavailable(BlockchainError):
    code = 'rpc_unavailable'
    http_status = 502
    default_message = 'ارتباط با شبکه بلاکچین برقرار نشد، کمی بعد دوباره تلاش کنید.'


class InvalidInput(BlockchainError):
    code = 'invalid_input'
    http_status = 400
    default_message = 'ورودی نامعتبر است.'


class ContractRevert(BlockchainError):
    """The contract rejected the call. `code` is the Solidity error name (e.g. 'ContestNotActive')."""

    http_status = 400
    default_message = 'قرارداد هوشمند این درخواست را رد کرد.'

    def __init__(self, error_name, args=None, raw=None):
        self.error_name = error_name
        self.args_dict = args or {}
        details = {'args': self.args_dict} if self.args_dict else {}
        if raw:
            details['raw'] = raw
        super().__init__(CONTRACT_ERROR_MESSAGES.get(error_name), code=error_name, details=details)
