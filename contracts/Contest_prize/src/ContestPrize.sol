// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";

/// @title ContestPrize
/// @notice Holds the entry fees / prize budget of every MathBot contest and pays the winners.
/// @dev The contest ID is the same as the `Contest` primary key in the Django database.
///      Every wei the contract holds belongs to exactly one contest, so the sum of all
///      `Total_amount` values is always equal to the contract balance.
contract ContestPrize is Ownable, ReentrancyGuard, Pausable {
    constructor() Ownable(msg.sender) {}

    struct comp {
        uint256 Total_amount; // wei held for this contest (entry fees + budget - payouts)
        uint256 Price; // entry fee in wei, 0 = free contest
        uint64 signupDeadline; // unix time, signup is closed from this moment on
        uint32 participants; // wallets that are signed up and not refunded
        bool status; // true while the contest is running
        bool exist;
        bool cancelled; // cancelled contests refund the entry fee to every participant
    }

    // for save each contest with ID
    mapping(uint256 => comp) Components;
    // contest ID => wallet => backend user ID of the account that signed up (0 = not signed up)
    mapping(uint256 => mapping(address => uint256)) participantRef;

    error ContestAlreadyExists(uint256 id);
    error ContestNotFound(uint256 id);
    error ContestNotActive(uint256 id);
    error ContestStillActive(uint256 id);
    error ContestNotCancelled(uint256 id);
    error InvalidDeadline(uint64 deadline);
    error SignupClosed(uint256 id);
    error IncorrectPayment(uint256 expected, uint256 received);
    error InvalidUserRef();
    error AlreadyRegistered(uint256 id, address user);
    error NotRegistered(uint256 id, address user);
    error ZeroValue();
    error InvalidAddress(address account);
    error DuplicateWinner(address winner);
    error LengthMismatch();
    // Error for wrong percentage inputs
    error InvalidPercentage(uint256 sum);
    error InsufficientContestBalance(uint256 available, uint256 required);
    error NothingToWithdraw(uint256 id);
    error TransferFailed(address to, uint256 amount);
    error RenounceOwnershipDisabled();

    event ContestCreated(uint256 indexed ID, uint256 Price, uint64 signupDeadline, uint256 initialBudget);
    event SignupDeadlineUpdated(uint256 indexed ID, uint64 signupDeadline);
    event BudgetAdded(uint256 indexed ID, uint256 amount);
    event SignupCompleted(uint256 indexed ID, address indexed user, uint256 indexed userRef);
    event PrizePaid(uint256 indexed ID, address indexed winner, uint256 amount);
    event ContestFinished(uint256 indexed ID, uint256 totalPaid, uint256 remaining);
    event ContestCancelled(uint256 indexed ID);
    event Refunded(uint256 indexed ID, address indexed user, uint256 amount);
    event OwnerWithdrawal(uint256 indexed ID, address indexed to, uint256 amount);

    modifier CheckActive(uint256 id) {
        require(Components[id].status, ContestNotActive(id));
        _;
    }

    modifier ChecknotexistId(uint256 id) {
        require(!Components[id].exist, ContestAlreadyExists(id));
        _;
    }

    modifier CheckexistID(uint256 id) {
        require(Components[id].exist, ContestNotFound(id));
        _;
    }

    // ------------------------------------------------------------------
    // Contest management (owner = backend wallet)
    // ------------------------------------------------------------------

    // Defines a contest. `_Price` is the entry fee in wei (0 = free contest) and
    // `_signupDeadline` is the unix time when signup closes (normally the contest start time).
    // Any ETH sent with the call becomes the initial prize budget of the contest.
    function Addcomp(uint256 _ID, uint256 _Price, uint64 _signupDeadline)
        external
        payable
        onlyOwner
        ChecknotexistId(_ID)
        whenNotPaused
    {
        require(_signupDeadline > block.timestamp, InvalidDeadline(_signupDeadline));
        Components[_ID] = comp({
            Total_amount: msg.value,
            Price: _Price,
            signupDeadline: _signupDeadline,
            participants: 0,
            status: true,
            exist: true,
            cancelled: false
        });
        emit ContestCreated(_ID, _Price, _signupDeadline, msg.value);
    }

    // Moves the signup deadline, e.g. when the contest start time changes.
    function setSignupDeadline(uint256 _ID, uint64 _signupDeadline)
        external
        onlyOwner
        CheckexistID(_ID)
        CheckActive(_ID)
        whenNotPaused
    {
        require(_signupDeadline > block.timestamp, InvalidDeadline(_signupDeadline));
        Components[_ID].signupDeadline = _signupDeadline;
        emit SignupDeadlineUpdated(_ID, _signupDeadline);
    }

    // Adds prize budget to a running contest. Needed for free contests (they have no entry
    // fees), but it also works for paid contests as an extra/sponsored prize.
    function addbudgeforfreecomp(uint256 _ID)
        external
        payable
        onlyOwner
        CheckexistID(_ID)
        CheckActive(_ID)
        whenNotPaused
    {
        require(msg.value > 0, ZeroValue());
        Components[_ID].Total_amount += msg.value;
        emit BudgetAdded(_ID, msg.value);
    }

    // Cancels a running contest. Every participant can then get the entry fee back
    // (claimRefund / refundParticipants) and the owner can withdraw the rest of the budget.
    function cancelComp(uint256 _ID) external onlyOwner CheckexistID(_ID) CheckActive(_ID) whenNotPaused {
        Components[_ID].status = false;
        Components[_ID].cancelled = true;
        emit ContestCancelled(_ID);
    }

    // ------------------------------------------------------------------
    // Participants
    // ------------------------------------------------------------------

    // User signup. `_userRef` is the backend (Django) user ID of the account that signs up,
    // the backend uses it to verify that this wallet paid for that account.
    function signup(uint256 _ID, uint256 _userRef) external payable CheckexistID(_ID) CheckActive(_ID) whenNotPaused {
        comp storage c = Components[_ID];
        require(block.timestamp < c.signupDeadline, SignupClosed(_ID));
        require(msg.value == c.Price, IncorrectPayment(c.Price, msg.value));
        require(_userRef != 0, InvalidUserRef());
        require(participantRef[_ID][msg.sender] == 0, AlreadyRegistered(_ID, msg.sender));

        participantRef[_ID][msg.sender] = _userRef;
        c.participants += 1;
        c.Total_amount += msg.value;
        emit SignupCompleted(_ID, msg.sender, _userRef);
    }

    // A participant of a cancelled contest takes the entry fee back.
    function claimRefund(uint256 _ID) external CheckexistID(_ID) nonReentrant whenNotPaused {
        require(Components[_ID].cancelled, ContestNotCancelled(_ID));
        require(_refund(_ID, msg.sender), NotRegistered(_ID, msg.sender));
    }

    // Owner pushes the refunds of a cancelled contest, so users don't need to send a transaction.
    // Addresses that are not signed up (or were already refunded) are skipped.
    function refundParticipants(uint256 _ID, address[] calldata _users)
        external
        onlyOwner
        CheckexistID(_ID)
        nonReentrant
        whenNotPaused
    {
        require(Components[_ID].cancelled, ContestNotCancelled(_ID));
        for (uint256 i = 0; i < _users.length; i++) {
            _refund(_ID, _users[i]);
        }
    }

    // ------------------------------------------------------------------
    // Prize distribution (each one finishes the contest)
    // ------------------------------------------------------------------

    // Divides the prizes of a competition among the winners with predetermined percentages:
    // 30% first, 20% second, 10% third. The remaining 40% is the organizer's share.
    function Awardwinners(address payable _first, address payable _second, address payable _Third, uint256 _ID)
        external
        onlyOwner
        CheckexistID(_ID)
        CheckActive(_ID)
        nonReentrant
        whenNotPaused
    {
        uint256 award = Components[_ID].Total_amount;
        _payWinners(
            _ID, _top3(_first, _second, _Third), _amounts3((award * 30) / 100, (award * 20) / 100, (award * 10) / 100)
        );
    }

    // Distributes the prizes of a contest according to the given percentages (sum <= 100).
    function AwardWithPercentage(
        address payable _first,
        address payable _second,
        address payable _Third,
        uint256 percent1,
        uint256 percent2,
        uint256 percent3,
        uint256 _ID
    ) external onlyOwner CheckexistID(_ID) CheckActive(_ID) nonReentrant whenNotPaused {
        uint256 sum = percent1 + percent2 + percent3;
        require(sum <= 100, InvalidPercentage(sum));
        uint256 award = Components[_ID].Total_amount;
        _payWinners(
            _ID,
            _top3(_first, _second, _Third),
            _amounts3((award * percent1) / 100, (award * percent2) / 100, (award * percent3) / 100)
        );
    }

    // function for freecomp and 3 person winner get: It takes the addresses of the
    // top 3 people and the amount of wei awarded to each of them and distributes the prizes.
    function Awardforfree_comp(
        address payable _first,
        address payable _second,
        address payable _Third,
        uint256 value_first,
        uint256 value_second,
        uint256 value_Third,
        uint256 ID
    ) external onlyOwner CheckexistID(ID) CheckActive(ID) nonReentrant whenNotPaused {
        _payWinners(ID, _top3(_first, _second, _Third), _amounts3(value_first, value_second, value_Third));
    }

    // Gives 90% of the contest balance to the winner of a duel competition.
    function Awardforduel_comp(address payable _first, uint256 ID_comp)
        external
        onlyOwner
        CheckexistID(ID_comp)
        CheckActive(ID_comp)
        nonReentrant
        whenNotPaused
    {
        address payable[] memory winners = new address payable[](1);
        winners[0] = _first;
        uint256[] memory amounts = new uint256[](1);
        amounts[0] = (Components[ID_comp].Total_amount * 90) / 100;
        _payWinners(ID_comp, winners, amounts);
    }

    // Prize distribution for competitions with arbitrary winners and prizes (prize = amount in wei).
    function Awardforarbitrary_comp(address payable[] calldata winners, uint256[] calldata prize, uint256 ID)
        external
        onlyOwner
        CheckexistID(ID)
        CheckActive(ID)
        nonReentrant
        whenNotPaused
    {
        require(winners.length == prize.length && winners.length > 0, LengthMismatch());
        _payWinners(ID, winners, prize);
    }

    // Withdraws the organizer's share after the contest is finished. For a cancelled contest
    // the entry fees of the participants that are not refunded yet stay in the contract.
    function withdrawOwner(address payable _to, uint256 _ID)
        external
        onlyOwner
        CheckexistID(_ID)
        nonReentrant
        whenNotPaused
    {
        comp storage c = Components[_ID];
        require(!c.status, ContestStillActive(_ID));
        require(_to != address(0), InvalidAddress(_to));
        uint256 reserved = c.cancelled ? uint256(c.participants) * c.Price : 0;
        uint256 amount = c.Total_amount - reserved;
        require(amount > 0, NothingToWithdraw(_ID));

        c.Total_amount = reserved;
        _safetransfer(_to, amount);
        emit OwnerWithdrawal(_ID, _to, amount);
    }

    // ------------------------------------------------------------------
    // Views
    // ------------------------------------------------------------------

    // return total budget of a contest with get ID
    function getcomptotal(uint256 _ID) external view CheckexistID(_ID) returns (uint256) {
        return Components[_ID].Total_amount;
    }

    // just return Running or finished competition
    function getcompstatus(uint256 _ID) external view CheckexistID(_ID) returns (bool) {
        return Components[_ID].status;
    }

    // Checks whether or not there is a match with this ID.
    function getcompexist(uint256 _ID) external view returns (bool) {
        return Components[_ID].exist;
    }

    // Returns every field of a contest in one call.
    function getcomp(uint256 _ID) external view CheckexistID(_ID) returns (comp memory) {
        return Components[_ID];
    }

    // Backend user ID that signed up with `_user` in contest `_ID` (0 = not signed up).
    function getParticipantRef(uint256 _ID, address _user) external view returns (uint256) {
        return participantRef[_ID][_user];
    }

    function isRegistered(uint256 _ID, address _user) external view returns (bool) {
        return participantRef[_ID][_user] != 0;
    }

    // True when signup() would currently accept a new participant.
    function isSignupOpen(uint256 _ID) external view returns (bool) {
        comp storage c = Components[_ID];
        return c.status && !paused() && block.timestamp < c.signupDeadline;
    }

    // ------------------------------------------------------------------
    // Emergency
    // ------------------------------------------------------------------

    // if contract We encountered a problem, contract owner can stop the work
    function pause() external onlyOwner {
        _pause();
    }

    // resumes the contract after pause
    function unpause() external onlyOwner {
        _unpause();
    }

    // Renouncing would lock every contest balance in the contract forever.
    function renounceOwnership() public pure override {
        revert RenounceOwnershipDisabled();
    }

    // ------------------------------------------------------------------
    // Internal
    // ------------------------------------------------------------------

    // Checks the payouts against the contest balance, finishes the contest and then pays
    // (state is updated before any external call).
    function _payWinners(uint256 _ID, address payable[] memory winners, uint256[] memory amounts) internal {
        comp storage c = Components[_ID];
        uint256 total;
        for (uint256 i = 0; i < winners.length; i++) {
            require(winners[i] != address(0), InvalidAddress(winners[i]));
            total += amounts[i];
        }
        require(total <= c.Total_amount, InsufficientContestBalance(c.Total_amount, total));

        c.status = false;
        c.Total_amount -= total;
        for (uint256 i = 0; i < winners.length; i++) {
            if (amounts[i] > 0) {
                _safetransfer(winners[i], amounts[i]);
            }
            emit PrizePaid(_ID, winners[i], amounts[i]);
        }
        emit ContestFinished(_ID, total, c.Total_amount);
    }

    function _refund(uint256 _ID, address _user) internal returns (bool) {
        if (participantRef[_ID][_user] == 0) return false;
        comp storage c = Components[_ID];
        uint256 amount = c.Price;

        delete participantRef[_ID][_user];
        c.participants -= 1;
        c.Total_amount -= amount;
        if (amount > 0) {
            _safetransfer(payable(_user), amount);
        }
        emit Refunded(_ID, _user, amount);
        return true;
    }

    function _top3(address payable _first, address payable _second, address payable _Third)
        internal
        pure
        returns (address payable[] memory winners)
    {
        require(_first != address(0), InvalidAddress(_first));
        require(_second != address(0), InvalidAddress(_second));
        require(_Third != address(0), InvalidAddress(_Third));
        require(_first != _second && _first != _Third, DuplicateWinner(_first));
        require(_second != _Third, DuplicateWinner(_second));
        winners = new address payable[](3);
        winners[0] = _first;
        winners[1] = _second;
        winners[2] = _Third;
    }

    function _amounts3(uint256 a, uint256 b, uint256 c) internal pure returns (uint256[] memory amounts) {
        amounts = new uint256[](3);
        amounts[0] = a;
        amounts[1] = b;
        amounts[2] = c;
    }

    // Internal function to safely transfer Ether
    function _safetransfer(address payable recipient, uint256 amount) internal {
        (bool success,) = recipient.call{value: amount}("");
        require(success, TransferFailed(recipient, amount));
    }
}
