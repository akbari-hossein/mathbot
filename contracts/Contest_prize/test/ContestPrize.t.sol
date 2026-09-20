// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import "forge-std/Test.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import "../src/ContestPrize.sol";

// Rejects every ETH transfer (e.g. a contract wallet without receive()).
contract RejectingReceiver {
    receive() external payable {
        revert("no ETH");
    }
}

// Signs up in a contest and tries to claim the refund twice from inside receive().
contract ReentrantRefunder {
    ContestPrize immutable target;
    uint256 immutable id;
    bool public reentered;

    constructor(ContestPrize _target, uint256 _id) {
        target = _target;
        id = _id;
    }

    function signup(uint256 price) external {
        target.signup{value: price}(id, 42);
    }

    function claim() external {
        target.claimRefund(id);
    }

    receive() external payable {
        if (!reentered) {
            reentered = true;
            target.claimRefund(id);
        }
    }
}

contract ContestPrizeTest is Test {
    ContestPrize _contestPrize;

    address alice = makeAddr("alice");
    address bob = makeAddr("bob");
    address carol = makeAddr("carol");
    address dave = makeAddr("dave");
    address treasury = makeAddr("treasury");
    address stranger = makeAddr("stranger");

    uint64 deadline;

    event ContestCreated(uint256 indexed ID, uint256 Price, uint64 signupDeadline, uint256 initialBudget);
    event SignupDeadlineUpdated(uint256 indexed ID, uint64 signupDeadline);
    event BudgetAdded(uint256 indexed ID, uint256 amount);
    event SignupCompleted(uint256 indexed ID, address indexed user, uint256 indexed userRef);
    event PrizePaid(uint256 indexed ID, address indexed winner, uint256 amount);
    event ContestFinished(uint256 indexed ID, uint256 totalPaid, uint256 remaining);
    event ContestCancelled(uint256 indexed ID);
    event Refunded(uint256 indexed ID, address indexed user, uint256 amount);
    event OwnerWithdrawal(uint256 indexed ID, address indexed to, uint256 amount);

    function setUp() public {
        _contestPrize = new ContestPrize();
        deadline = uint64(block.timestamp + 1 days);
        vm.deal(address(this), 1000 ether);
        vm.deal(alice, 100 ether);
        vm.deal(bob, 100 ether);
        vm.deal(carol, 100 ether);
        vm.deal(dave, 100 ether);
    }

    // ------------------------------------------------------------------
    // helpers
    // ------------------------------------------------------------------

    function _signup(address user, uint256 id, uint256 ref) internal {
        uint256 price = _contestPrize.getcomp(id).Price;
        vm.prank(user);
        _contestPrize.signup{value: price}(id, ref);
    }

    // paid contest 1 (1 ETH) with alice, bob, carol, dave -> 4 ETH in the pool
    function _paidContestWith4Players() internal {
        _contestPrize.Addcomp(1, 1 ether, deadline);
        _signup(alice, 1, 11);
        _signup(bob, 1, 12);
        _signup(carol, 1, 13);
        _signup(dave, 1, 14);
    }

    function _err(bytes4 selector, uint256 id) internal pure returns (bytes memory) {
        return abi.encodeWithSelector(selector, id);
    }

    // ------------------------------------------------------------------
    // Addcomp
    // ------------------------------------------------------------------

    function testaddcomp() public {
        vm.expectEmit(address(_contestPrize));
        emit ContestCreated(1, 10, deadline, 0);
        _contestPrize.Addcomp(1, 10, deadline);

        ContestPrize.comp memory c = _contestPrize.getcomp(1);
        assertEq(c.Total_amount, 0);
        assertEq(c.Price, 10);
        assertEq(c.signupDeadline, deadline);
        assertEq(c.participants, 0);
        assertTrue(c.status);
        assertTrue(c.exist);
        assertFalse(c.cancelled);

        vm.expectRevert(_err(ContestPrize.ContestAlreadyExists.selector, 1));
        _contestPrize.Addcomp(1, 10, deadline);

        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, stranger));
        _contestPrize.Addcomp(2, 2, deadline);
    }

    function testaddcompWithInitialBudget() public {
        _contestPrize.Addcomp{value: 3 ether}(1, 0, deadline);
        assertEq(_contestPrize.getcomptotal(1), 3 ether);
        assertEq(address(_contestPrize).balance, 3 ether);
    }

    function testaddcompRejectsPastDeadline() public {
        vm.warp(1000);
        vm.expectRevert(abi.encodeWithSelector(ContestPrize.InvalidDeadline.selector, uint64(1000)));
        _contestPrize.Addcomp(1, 1, 1000);
        vm.expectRevert(abi.encodeWithSelector(ContestPrize.InvalidDeadline.selector, uint64(999)));
        _contestPrize.Addcomp(1, 1, 999);
    }

    // ------------------------------------------------------------------
    // setSignupDeadline
    // ------------------------------------------------------------------

    function testsetsignupdeadline() public {
        _contestPrize.Addcomp(1, 1 ether, deadline);
        uint64 later = deadline + 1 days;

        vm.expectEmit(address(_contestPrize));
        emit SignupDeadlineUpdated(1, later);
        _contestPrize.setSignupDeadline(1, later);
        assertEq(_contestPrize.getcomp(1).signupDeadline, later);

        vm.expectRevert(abi.encodeWithSelector(ContestPrize.InvalidDeadline.selector, uint64(block.timestamp)));
        _contestPrize.setSignupDeadline(1, uint64(block.timestamp));

        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, stranger));
        _contestPrize.setSignupDeadline(1, later);

        vm.expectRevert(_err(ContestPrize.ContestNotFound.selector, 2));
        _contestPrize.setSignupDeadline(2, later);
    }

    function testsetsignupdeadlineReopensSignup() public {
        _contestPrize.Addcomp(1, 1 ether, deadline);
        vm.warp(deadline);
        assertFalse(_contestPrize.isSignupOpen(1));
        _contestPrize.setSignupDeadline(1, deadline + 1 hours);
        assertTrue(_contestPrize.isSignupOpen(1));
        _signup(alice, 1, 11);
    }

    // ------------------------------------------------------------------
    // signup
    // ------------------------------------------------------------------

    function testsignup() public {
        _contestPrize.Addcomp(1, 10 ether, deadline);
        vm.expectRevert(_err(ContestPrize.ContestNotFound.selector, 2));
        _contestPrize.signup(2, 1);

        vm.expectEmit(address(_contestPrize));
        emit SignupCompleted(1, alice, 7);
        vm.prank(alice);
        _contestPrize.signup{value: 10 ether}(1, 7);

        assertEq(address(_contestPrize).balance, 10 ether);
        assertEq(_contestPrize.getcomptotal(1), 10 ether);
        assertEq(_contestPrize.getcomp(1).participants, 1);
        assertEq(_contestPrize.getParticipantRef(1, alice), 7);
        assertTrue(_contestPrize.isRegistered(1, alice));
        assertFalse(_contestPrize.isRegistered(1, bob));
    }

    function testsignupFreeContest() public {
        _contestPrize.Addcomp(1, 0, deadline);
        vm.prank(alice);
        _contestPrize.signup(1, 5);
        assertTrue(_contestPrize.isRegistered(1, alice));
        assertEq(_contestPrize.getcomptotal(1), 0);
    }

    function testsignupWrongAmount() public {
        _contestPrize.Addcomp(1, 1 ether, deadline);
        vm.startPrank(alice);
        vm.expectRevert(abi.encodeWithSelector(ContestPrize.IncorrectPayment.selector, 1 ether, 0.5 ether));
        _contestPrize.signup{value: 0.5 ether}(1, 1);
        vm.expectRevert(abi.encodeWithSelector(ContestPrize.IncorrectPayment.selector, 1 ether, 2 ether));
        _contestPrize.signup{value: 2 ether}(1, 1);
        vm.stopPrank();
    }

    // regression: the same wallet could pay the entry fee twice
    function testsignupTwiceReverts() public {
        _contestPrize.Addcomp(1, 1 ether, deadline);
        _signup(alice, 1, 1);
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(ContestPrize.AlreadyRegistered.selector, 1, alice));
        _contestPrize.signup{value: 1 ether}(1, 2);
        assertEq(_contestPrize.getcomptotal(1), 1 ether);
    }

    function testsignupZeroUserRefReverts() public {
        _contestPrize.Addcomp(1, 1 ether, deadline);
        vm.prank(alice);
        vm.expectRevert(ContestPrize.InvalidUserRef.selector);
        _contestPrize.signup{value: 1 ether}(1, 0);
    }

    function testsignupClosesAtDeadline() public {
        _contestPrize.Addcomp(1, 1 ether, deadline);
        vm.warp(deadline - 1);
        _signup(alice, 1, 1);
        vm.warp(deadline);
        vm.prank(bob);
        vm.expectRevert(_err(ContestPrize.SignupClosed.selector, 1));
        _contestPrize.signup{value: 1 ether}(1, 2);
    }

    function testsignupAfterFinishReverts() public {
        _contestPrize.Addcomp{value: 1 ether}(1, 0, deadline);
        _contestPrize.Awardforduel_comp(payable(alice), 1);
        vm.prank(bob);
        vm.expectRevert(_err(ContestPrize.ContestNotActive.selector, 1));
        _contestPrize.signup(1, 2);
    }

    // regression: a plain ETH transfer was accepted but never registered the user
    function testplainTransferIsRejected() public {
        _contestPrize.Addcomp(1, 1 ether, deadline);
        vm.prank(alice);
        (bool ok,) = address(_contestPrize).call{value: 1 ether}("");
        assertFalse(ok);
        assertEq(address(_contestPrize).balance, 0);
        assertEq(alice.balance, 100 ether);
    }

    // ------------------------------------------------------------------
    // addbudgeforfreecomp
    // ------------------------------------------------------------------

    function testaddbudgetfreecomp() public {
        _contestPrize.Addcomp(1, 0, deadline);
        vm.expectEmit(address(_contestPrize));
        emit BudgetAdded(1, 5 ether);
        _contestPrize.addbudgeforfreecomp{value: 5 ether}(1);
        assertEq(_contestPrize.getcomptotal(1), 5 ether);

        vm.expectRevert(ContestPrize.ZeroValue.selector);
        _contestPrize.addbudgeforfreecomp{value: 0}(1);

        vm.expectRevert(_err(ContestPrize.ContestNotFound.selector, 2));
        _contestPrize.addbudgeforfreecomp{value: 1 ether}(2);

        vm.deal(stranger, 1 ether);
        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, stranger));
        _contestPrize.addbudgeforfreecomp{value: 1 ether}(1);
    }

    // regression: a second deposit was not added to the contest total and got stuck
    function testaddbudgetTwiceIsTracked() public {
        _contestPrize.Addcomp(1, 0, deadline);
        _contestPrize.addbudgeforfreecomp{value: 1 ether}(1);
        _contestPrize.addbudgeforfreecomp{value: 1 ether}(1);
        assertEq(_contestPrize.getcomptotal(1), 2 ether);
        assertEq(address(_contestPrize).balance, 2 ether);
    }

    function testaddbudgetOnPaidContest() public {
        _paidContestWith4Players();
        _contestPrize.addbudgeforfreecomp{value: 6 ether}(1);
        assertEq(_contestPrize.getcomptotal(1), 10 ether);
    }

    // ------------------------------------------------------------------
    // Awardwinners (30 / 20 / 10)
    // ------------------------------------------------------------------

    function testawardwinners() public {
        _contestPrize.Addcomp{value: 100 ether}(1, 0, deadline);
        address w1 = makeAddr("w1");
        address w2 = makeAddr("w2");
        address w3 = makeAddr("w3");

        vm.expectEmit(address(_contestPrize));
        emit PrizePaid(1, w1, 30 ether);
        vm.expectEmit(address(_contestPrize));
        emit PrizePaid(1, w2, 20 ether);
        vm.expectEmit(address(_contestPrize));
        emit PrizePaid(1, w3, 10 ether);
        vm.expectEmit(address(_contestPrize));
        emit ContestFinished(1, 60 ether, 40 ether);
        _contestPrize.Awardwinners(payable(w1), payable(w2), payable(w3), 1);

        assertEq(w1.balance, 30 ether);
        assertEq(w2.balance, 20 ether);
        assertEq(w3.balance, 10 ether);
        assertEq(_contestPrize.getcomptotal(1), 40 ether);
        assertFalse(_contestPrize.getcompstatus(1));
    }

    function testawardwinnersFromEntryFees() public {
        _paidContestWith4Players();
        _contestPrize.Awardwinners(payable(alice), payable(bob), payable(carol), 1);
        assertEq(alice.balance, 99 ether + 1.2 ether);
        assertEq(bob.balance, 99 ether + 0.8 ether);
        assertEq(carol.balance, 99 ether + 0.4 ether);
        assertEq(_contestPrize.getcomptotal(1), 1.6 ether);
    }

    function testawardwinnersValidation() public {
        _paidContestWith4Players();
        vm.expectRevert(abi.encodeWithSelector(ContestPrize.InvalidAddress.selector, address(0)));
        _contestPrize.Awardwinners(payable(address(0)), payable(bob), payable(carol), 1);
        vm.expectRevert(abi.encodeWithSelector(ContestPrize.InvalidAddress.selector, address(0)));
        _contestPrize.Awardwinners(payable(alice), payable(address(0)), payable(carol), 1);
        vm.expectRevert(abi.encodeWithSelector(ContestPrize.InvalidAddress.selector, address(0)));
        _contestPrize.Awardwinners(payable(alice), payable(bob), payable(address(0)), 1);
        vm.expectRevert(abi.encodeWithSelector(ContestPrize.DuplicateWinner.selector, alice));
        _contestPrize.Awardwinners(payable(alice), payable(bob), payable(alice), 1);
        vm.expectRevert(abi.encodeWithSelector(ContestPrize.DuplicateWinner.selector, bob));
        _contestPrize.Awardwinners(payable(alice), payable(bob), payable(bob), 1);

        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, stranger));
        _contestPrize.Awardwinners(payable(alice), payable(bob), payable(carol), 1);

        _contestPrize.Awardwinners(payable(alice), payable(bob), payable(carol), 1);
        vm.expectRevert(_err(ContestPrize.ContestNotActive.selector, 1));
        _contestPrize.Awardwinners(payable(alice), payable(bob), payable(carol), 1);
    }

    // ------------------------------------------------------------------
    // AwardWithPercentage
    // ------------------------------------------------------------------

    function testawardwithpercentage() public {
        _contestPrize.Addcomp{value: 100 ether}(1, 0, deadline);
        _contestPrize.AwardWithPercentage(payable(alice), payable(bob), payable(carol), 50, 30, 5, 1);
        assertEq(alice.balance, 150 ether);
        assertEq(bob.balance, 130 ether);
        assertEq(carol.balance, 105 ether);
        assertEq(_contestPrize.getcomptotal(1), 15 ether);
    }

    function testawardwithpercentageOver100Reverts() public {
        _contestPrize.Addcomp{value: 100 ether}(1, 0, deadline);
        vm.expectRevert(abi.encodeWithSelector(ContestPrize.InvalidPercentage.selector, 101));
        _contestPrize.AwardWithPercentage(payable(alice), payable(bob), payable(carol), 50, 50, 1, 1);
    }

    function testawardwithpercentageZeroShare() public {
        _contestPrize.Addcomp{value: 10 ether}(1, 0, deadline);
        _contestPrize.AwardWithPercentage(payable(alice), payable(bob), payable(carol), 100, 0, 0, 1);
        assertEq(alice.balance, 110 ether);
        assertEq(bob.balance, 100 ether);
        assertEq(_contestPrize.getcomptotal(1), 0);
    }

    // ------------------------------------------------------------------
    // Awardforfree_comp
    // ------------------------------------------------------------------

    function testawardforfreecomp() public {
        _contestPrize.Addcomp{value: 100 ether}(1, 0, deadline);
        _contestPrize.Awardforfree_comp(payable(alice), payable(bob), payable(carol), 50 ether, 30 ether, 5 ether, 1);
        assertEq(alice.balance, 150 ether);
        assertEq(bob.balance, 130 ether);
        assertEq(carol.balance, 105 ether);
        assertEq(_contestPrize.getcomptotal(1), 15 ether);
    }

    // regression: an unfunded free contest paid its prizes with other contests' entry fees
    function testunfundedFreeContestCannotUseOtherContestsMoney() public {
        _paidContestWith4Players(); // 4 ETH of user money in contest 1
        _contestPrize.Addcomp(2, 0, deadline); // free contest, not funded

        vm.expectRevert(abi.encodeWithSelector(ContestPrize.InsufficientContestBalance.selector, 0, 3 ether));
        _contestPrize.Awardforfree_comp(payable(alice), payable(bob), payable(carol), 1 ether, 1 ether, 1 ether, 2);

        _contestPrize.Awardforduel_comp(payable(stranger), 2); // 90% of 0
        assertEq(stranger.balance, 0);
        assertEq(address(_contestPrize).balance, 4 ether);
        assertEq(_contestPrize.getcomptotal(1), 4 ether);
    }

    // ------------------------------------------------------------------
    // Awardforduel_comp
    // ------------------------------------------------------------------

    function testawardforduel() public {
        _contestPrize.Addcomp(1, 5 ether, deadline);
        _signup(alice, 1, 1);
        _signup(bob, 1, 2);
        _contestPrize.Awardforduel_comp(payable(bob), 1);
        assertEq(bob.balance, 95 ether + 9 ether);
        assertEq(_contestPrize.getcomptotal(1), 1 ether);

        _contestPrize.Addcomp{value: 1 ether}(2, 0, deadline);
        vm.expectRevert(abi.encodeWithSelector(ContestPrize.InvalidAddress.selector, address(0)));
        _contestPrize.Awardforduel_comp(payable(address(0)), 2);
    }

    // ------------------------------------------------------------------
    // Awardforarbitrary_comp
    // ------------------------------------------------------------------

    function testawardforarbitrary() public {
        address payable[] memory winners = new address payable[](3);
        winners[0] = payable(alice);
        winners[1] = payable(bob);
        winners[2] = payable(carol);
        uint256[] memory amounts = new uint256[](3);
        amounts[0] = 50 ether;
        amounts[1] = 30 ether;
        amounts[2] = 5 ether;
        _contestPrize.Addcomp{value: 100 ether}(1, 0, deadline);
        _contestPrize.Awardforarbitrary_comp(winners, amounts, 1);
        assertEq(alice.balance, 150 ether);
        assertEq(bob.balance, 130 ether);
        assertEq(carol.balance, 105 ether);
        assertEq(_contestPrize.getcomptotal(1), 15 ether);
    }

    // regression: the unchecked subtraction let a contest pay more than it holds
    function testawardforarbitraryCannotOverpay() public {
        _contestPrize.Addcomp(1, 1 ether, deadline);
        _signup(alice, 1, 1);
        _contestPrize.Addcomp(2, 5 ether, deadline);
        _signup(bob, 2, 2);

        address payable[] memory winners = new address payable[](1);
        winners[0] = payable(stranger);
        uint256[] memory amounts = new uint256[](1);
        amounts[0] = 6 ether;
        vm.expectRevert(abi.encodeWithSelector(ContestPrize.InsufficientContestBalance.selector, 1 ether, 6 ether));
        _contestPrize.Awardforarbitrary_comp(winners, amounts, 1);

        assertEq(_contestPrize.getcomptotal(1), 1 ether);
        assertEq(_contestPrize.getcomptotal(2), 5 ether);
        assertEq(address(_contestPrize).balance, 6 ether);
    }

    function testawardforarbitraryValidation() public {
        _contestPrize.Addcomp{value: 1 ether}(1, 0, deadline);
        address payable[] memory winners = new address payable[](2);
        winners[0] = payable(alice);
        winners[1] = payable(address(0));
        uint256[] memory amounts = new uint256[](1);

        vm.expectRevert(ContestPrize.LengthMismatch.selector);
        _contestPrize.Awardforarbitrary_comp(winners, amounts, 1);
        vm.expectRevert(ContestPrize.LengthMismatch.selector);
        _contestPrize.Awardforarbitrary_comp(new address payable[](0), new uint256[](0), 1);

        amounts = new uint256[](2);
        vm.expectRevert(abi.encodeWithSelector(ContestPrize.InvalidAddress.selector, address(0)));
        _contestPrize.Awardforarbitrary_comp(winners, amounts, 1);
    }

    // ------------------------------------------------------------------
    // withdrawOwner
    // ------------------------------------------------------------------

    function testwithdrawowner() public {
        _contestPrize.Addcomp{value: 100 ether}(1, 0, deadline);
        _contestPrize.Awardforduel_comp(payable(alice), 1);
        assertEq(alice.balance, 190 ether);

        vm.expectEmit(address(_contestPrize));
        emit OwnerWithdrawal(1, treasury, 10 ether);
        _contestPrize.withdrawOwner(payable(treasury), 1);
        assertEq(treasury.balance, 10 ether);
        assertEq(_contestPrize.getcomptotal(1), 0);

        vm.expectRevert(_err(ContestPrize.NothingToWithdraw.selector, 1));
        _contestPrize.withdrawOwner(payable(treasury), 1);
    }

    // test finish comp and only owner can withdraw
    function testfinishcomp() public {
        _contestPrize.Addcomp{value: 20 ether}(1, 0, deadline);
        vm.expectRevert(_err(ContestPrize.ContestStillActive.selector, 1));
        _contestPrize.withdrawOwner(payable(treasury), 1);

        _contestPrize.Awardforduel_comp(payable(alice), 1);
        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, stranger));
        _contestPrize.withdrawOwner(payable(stranger), 1);

        vm.expectRevert(abi.encodeWithSelector(ContestPrize.InvalidAddress.selector, address(0)));
        _contestPrize.withdrawOwner(payable(address(0)), 1);
    }

    function testwithdrawOnlyTouchesOwnContest() public {
        _paidContestWith4Players();
        _contestPrize.Addcomp{value: 10 ether}(2, 0, deadline);
        _contestPrize.Awardforduel_comp(payable(alice), 2);
        _contestPrize.withdrawOwner(payable(treasury), 2);
        assertEq(treasury.balance, 1 ether);
        assertEq(address(_contestPrize).balance, 4 ether);
        assertEq(_contestPrize.getcomptotal(1), 4 ether);
    }

    // ------------------------------------------------------------------
    // cancel & refunds
    // ------------------------------------------------------------------

    function testcancelAndClaimRefund() public {
        _paidContestWith4Players();

        vm.expectEmit(address(_contestPrize));
        emit ContestCancelled(1);
        _contestPrize.cancelComp(1);
        ContestPrize.comp memory c = _contestPrize.getcomp(1);
        assertFalse(c.status);
        assertTrue(c.cancelled);

        vm.expectEmit(address(_contestPrize));
        emit Refunded(1, alice, 1 ether);
        vm.prank(alice);
        _contestPrize.claimRefund(1);
        assertEq(alice.balance, 100 ether);
        assertFalse(_contestPrize.isRegistered(1, alice));
        assertEq(_contestPrize.getcomp(1).participants, 3);
        assertEq(_contestPrize.getcomptotal(1), 3 ether);

        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(ContestPrize.NotRegistered.selector, 1, alice));
        _contestPrize.claimRefund(1);

        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(ContestPrize.NotRegistered.selector, 1, stranger));
        _contestPrize.claimRefund(1);
    }

    function testclaimRefundRequiresCancelled() public {
        _paidContestWith4Players();
        vm.prank(alice);
        vm.expectRevert(_err(ContestPrize.ContestNotCancelled.selector, 1));
        _contestPrize.claimRefund(1);

        _contestPrize.Awardwinners(payable(alice), payable(bob), payable(carol), 1);
        vm.prank(dave);
        vm.expectRevert(_err(ContestPrize.ContestNotCancelled.selector, 1));
        _contestPrize.claimRefund(1);
    }

    function testrefundParticipantsBatch() public {
        _paidContestWith4Players();
        _contestPrize.cancelComp(1);

        vm.prank(bob);
        _contestPrize.claimRefund(1);

        address[] memory users = new address[](4);
        users[0] = alice;
        users[1] = bob; // already refunded -> skipped
        users[2] = stranger; // never signed up -> skipped
        users[3] = carol;
        _contestPrize.refundParticipants(1, users);

        assertEq(alice.balance, 100 ether);
        assertEq(bob.balance, 100 ether);
        assertEq(carol.balance, 100 ether);
        assertEq(dave.balance, 99 ether);
        assertEq(_contestPrize.getcomp(1).participants, 1);
        assertEq(_contestPrize.getcomptotal(1), 1 ether);

        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, stranger));
        _contestPrize.refundParticipants(1, users);
    }

    function testwithdrawFromCancelledKeepsRefunds() public {
        _paidContestWith4Players(); // 4 ETH fees
        _contestPrize.addbudgeforfreecomp{value: 2 ether}(1); // + 2 ETH budget
        _contestPrize.cancelComp(1);

        _contestPrize.withdrawOwner(payable(treasury), 1);
        assertEq(treasury.balance, 2 ether);
        assertEq(_contestPrize.getcomptotal(1), 4 ether);

        vm.expectRevert(_err(ContestPrize.NothingToWithdraw.selector, 1));
        _contestPrize.withdrawOwner(payable(treasury), 1);

        vm.prank(alice);
        _contestPrize.claimRefund(1);
        vm.prank(dave);
        _contestPrize.claimRefund(1);
        assertEq(_contestPrize.getcomptotal(1), 2 ether);
        assertEq(address(_contestPrize).balance, 2 ether);
    }

    function testcancelValidation() public {
        _contestPrize.Addcomp{value: 1 ether}(1, 0, deadline);
        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, stranger));
        _contestPrize.cancelComp(1);

        _contestPrize.Awardforduel_comp(payable(alice), 1);
        vm.expectRevert(_err(ContestPrize.ContestNotActive.selector, 1));
        _contestPrize.cancelComp(1);
    }

    function testcancelledContestCannotBeAwarded() public {
        _paidContestWith4Players();
        _contestPrize.cancelComp(1);
        vm.expectRevert(_err(ContestPrize.ContestNotActive.selector, 1));
        _contestPrize.Awardforduel_comp(payable(alice), 1);
    }

    // ------------------------------------------------------------------
    // failing / malicious receivers
    // ------------------------------------------------------------------

    function testrejectingWinnerRevertsWholeAward() public {
        _contestPrize.Addcomp{value: 10 ether}(1, 0, deadline);
        RejectingReceiver bad = new RejectingReceiver();
        vm.expectRevert(abi.encodeWithSelector(ContestPrize.TransferFailed.selector, address(bad), 9 ether));
        _contestPrize.Awardforduel_comp(payable(address(bad)), 1);

        // nothing changed, the owner can award another address
        assertTrue(_contestPrize.getcompstatus(1));
        assertEq(_contestPrize.getcomptotal(1), 10 ether);
        _contestPrize.Awardforduel_comp(payable(alice), 1);
        assertEq(alice.balance, 109 ether);
    }

    function testreentrantRefundFails() public {
        _contestPrize.Addcomp(1, 1 ether, deadline);
        _signup(alice, 1, 1);
        ReentrantRefunder attacker = new ReentrantRefunder(_contestPrize, 1);
        vm.deal(address(attacker), 1 ether);
        attacker.signup(1 ether);
        _contestPrize.cancelComp(1);

        vm.expectRevert(abi.encodeWithSelector(ContestPrize.TransferFailed.selector, address(attacker), 1 ether));
        attacker.claim();
        assertEq(address(_contestPrize).balance, 2 ether);
        assertEq(_contestPrize.getcomptotal(1), 2 ether);
    }

    // ------------------------------------------------------------------
    // pause & ownership
    // ------------------------------------------------------------------

    function testpause() public {
        _contestPrize.pause();
        vm.expectRevert(Pausable.EnforcedPause.selector);
        _contestPrize.Addcomp(1, 20, deadline);
        _contestPrize.unpause();
        _contestPrize.Addcomp(2, 30, deadline);

        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, stranger));
        _contestPrize.pause();
    }

    function testpauseBlocksMoneyMovement() public {
        _paidContestWith4Players();
        _contestPrize.Addcomp(2, 1 ether, deadline);
        _signup(alice, 2, 1);
        _contestPrize.cancelComp(2);
        _contestPrize.pause();

        _contestPrize.unpause();
        _contestPrize.Addcomp(3, 1 ether, deadline);
        _contestPrize.pause();
        vm.prank(bob);
        vm.expectRevert(Pausable.EnforcedPause.selector);
        _contestPrize.signup{value: 1 ether}(3, 2);

        vm.expectRevert(Pausable.EnforcedPause.selector);
        _contestPrize.Awardwinners(payable(alice), payable(bob), payable(carol), 1);

        vm.expectRevert(Pausable.EnforcedPause.selector);
        _contestPrize.withdrawOwner(payable(treasury), 2);

        vm.prank(alice);
        vm.expectRevert(Pausable.EnforcedPause.selector);
        _contestPrize.claimRefund(2);

        assertFalse(_contestPrize.isSignupOpen(1));
        assertEq(_contestPrize.getcomptotal(1), 4 ether); // views still work

        _contestPrize.unpause();
        assertTrue(_contestPrize.isSignupOpen(1));
    }

    function testrenounceOwnershipDisabled() public {
        vm.expectRevert(ContestPrize.RenounceOwnershipDisabled.selector);
        _contestPrize.renounceOwnership();
        assertEq(_contestPrize.owner(), address(this));
    }

    function testtransferOwnership() public {
        _contestPrize.transferOwnership(treasury);
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, address(this)));
        _contestPrize.Addcomp(1, 1, deadline);
        vm.prank(treasury);
        _contestPrize.Addcomp(1, 1, deadline);
    }

    // ------------------------------------------------------------------
    // views
    // ------------------------------------------------------------------

    function testviewsOnMissingContest() public {
        assertFalse(_contestPrize.getcompexist(9));
        assertFalse(_contestPrize.isSignupOpen(9));
        assertFalse(_contestPrize.isRegistered(9, alice));
        assertEq(_contestPrize.getParticipantRef(9, alice), 0);
        vm.expectRevert(_err(ContestPrize.ContestNotFound.selector, 9));
        _contestPrize.getcomptotal(9);
        vm.expectRevert(_err(ContestPrize.ContestNotFound.selector, 9));
        _contestPrize.getcompstatus(9);
        vm.expectRevert(_err(ContestPrize.ContestNotFound.selector, 9));
        _contestPrize.getcomp(9);
    }

    function testisSignupOpenLifecycle() public {
        _contestPrize.Addcomp(1, 1 ether, deadline);
        assertTrue(_contestPrize.getcompexist(1));
        assertTrue(_contestPrize.isSignupOpen(1));
        vm.warp(deadline);
        assertFalse(_contestPrize.isSignupOpen(1));

        _contestPrize.Addcomp(2, 0, deadline + 1 days);
        _contestPrize.cancelComp(2);
        assertFalse(_contestPrize.isSignupOpen(2));
    }

    // ------------------------------------------------------------------
    // fuzz
    // ------------------------------------------------------------------

    function testFuzz_awardWithPercentageConservesFunds(uint256 budget, uint8 p1, uint8 p2, uint8 p3) public {
        vm.assume(uint256(p1) + p2 + p3 <= 100);
        budget = bound(budget, 0, 1000 ether);
        _contestPrize.Addcomp{value: budget}(1, 0, deadline);
        _contestPrize.AwardWithPercentage(payable(alice), payable(bob), payable(carol), p1, p2, p3, 1);

        uint256 paid = (alice.balance - 100 ether) + (bob.balance - 100 ether) + (carol.balance - 100 ether);
        assertEq(paid + _contestPrize.getcomptotal(1), budget);
        assertEq(address(_contestPrize).balance, _contestPrize.getcomptotal(1));
        assertLe(paid, budget);
    }

    function testFuzz_signupThenAwardWinners(uint8 players, uint64 price) public {
        players = uint8(bound(players, 3, 40));
        price = uint64(bound(price, 1, 10 ether));
        _contestPrize.Addcomp(1, price, deadline);
        for (uint256 i = 0; i < players; i++) {
            address p = address(uint160(0x10000 + i));
            vm.deal(p, price);
            vm.prank(p);
            _contestPrize.signup{value: price}(1, i + 1);
        }
        uint256 pool = uint256(price) * players;
        assertEq(_contestPrize.getcomptotal(1), pool);
        assertEq(_contestPrize.getcomp(1).participants, players);

        _contestPrize.Awardwinners(payable(alice), payable(bob), payable(carol), 1);
        uint256 paid = (pool * 30) / 100 + (pool * 20) / 100 + (pool * 10) / 100;
        assertEq(_contestPrize.getcomptotal(1), pool - paid);

        _contestPrize.withdrawOwner(payable(treasury), 1);
        assertEq(treasury.balance, pool - paid);
        assertEq(address(_contestPrize).balance, 0);
    }

    function testFuzz_cancelRefundsEveryone(uint8 players, uint64 price, uint64 budget) public {
        players = uint8(bound(players, 1, 30));
        price = uint64(bound(price, 1, 10 ether));
        _contestPrize.Addcomp{value: budget}(1, price, deadline);
        for (uint256 i = 0; i < players; i++) {
            address p = address(uint160(0x10000 + i));
            vm.deal(p, price);
            vm.prank(p);
            _contestPrize.signup{value: price}(1, i + 1);
        }
        _contestPrize.cancelComp(1);
        if (budget > 0) {
            _contestPrize.withdrawOwner(payable(treasury), 1);
        }
        assertEq(treasury.balance, budget);
        for (uint256 i = 0; i < players; i++) {
            address p = address(uint160(0x10000 + i));
            vm.prank(p);
            _contestPrize.claimRefund(1);
            assertEq(p.balance, price);
        }
        assertEq(_contestPrize.getcomptotal(1), 0);
        assertEq(address(_contestPrize).balance, 0);
    }
}
