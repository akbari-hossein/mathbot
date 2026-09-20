// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import "forge-std/Test.sol";
import "../src/ContestPrize.sol";

// Owns the contract and performs random (but well-formed) actions on it.
contract ContestPrizeHandler is Test {
    ContestPrize public c;
    uint256[] public ids;
    address[] public players;
    address public treasury = makeAddr("treasury");
    uint256 nextId = 1;
    // how many calls really succeeded (shown with -vv, proves the success paths are exercised)
    uint256 public okSignups;
    uint256 public okAwards;
    uint256 public okCancels;
    uint256 public okRefunds;
    uint256 public okWithdrawals;

    constructor(ContestPrize _c) {
        c = _c;
        for (uint256 i = 0; i < 6; i++) {
            players.push(makeAddr(string(abi.encodePacked("player", vm.toString(i)))));
        }
    }

    function idsLength() external view returns (uint256) {
        return ids.length;
    }

    // actions focus on the 3 newest contests so that signups, cancels and refunds hit the same contest
    function _id(uint256 seed) internal view returns (uint256) {
        uint256 window = ids.length < 3 ? ids.length : 3;
        return ids[ids.length - 1 - (seed % window)];
    }

    // a cancelled contest among the newest ones (falls back to _id), so refund actions hit something
    function _cancelledId(uint256 seed) internal view returns (uint256) {
        uint256 window = ids.length < 3 ? ids.length : 3;
        for (uint256 i = 0; i < window; i++) {
            uint256 id = ids[ids.length - 1 - i];
            if (c.getcomp(id).cancelled) return id;
        }
        return _id(seed);
    }

    // like a real admin: finish / cancel a contest only after people joined (sometimes earlier)
    function _ready(uint256 id, uint256 seed) internal view returns (bool) {
        return c.getcomp(id).participants >= 2 || seed % 8 == 0;
    }

    function _player(uint256 seed) internal view returns (address) {
        return players[seed % players.length];
    }

    function create(uint256 price, uint256 budget, uint256 duration) external {
        price = bound(price, 0, 5 ether);
        budget = bound(budget, 0, 20 ether);
        duration = bound(duration, 1 days, 60 days);
        vm.deal(address(this), budget);
        c.Addcomp{value: budget}(nextId, price, uint64(block.timestamp + duration));
        ids.push(nextId++);
    }

    // signs up 1..6 players at once, so contests get participants before they are finished
    function signup(uint256 idSeed, uint256 playerSeed, uint256 count) external {
        if (ids.length == 0) return;
        uint256 id = _id(idSeed);
        uint256 price = c.getcomp(id).Price;
        count = bound(count, 1, players.length);
        playerSeed = playerSeed % players.length;
        for (uint256 i = 0; i < count; i++) {
            address p = _player(playerSeed + i);
            vm.deal(p, p.balance + price);
            vm.prank(p);
            try c.signup{value: price}(id, (playerSeed + i) % 1000 + 1) {
                okSignups++;
            } catch {}
        }
    }

    function addBudget(uint256 idSeed, uint256 amount) external {
        if (ids.length == 0) return;
        amount = bound(amount, 1, 10 ether);
        vm.deal(address(this), amount);
        try c.addbudgeforfreecomp{value: amount}(_id(idSeed)) {} catch {}
    }

    function awardTop3(uint256 idSeed, uint256 mode, uint256 a, uint256 b, uint256 d) external {
        if (ids.length == 0) return;
        uint256 id = _id(idSeed);
        if (!_ready(id, mode)) return;
        address payable w1 = payable(players[0]);
        address payable w2 = payable(players[1]);
        address payable w3 = payable(players[2]);
        mode = mode % 3;
        if (mode == 0) {
            try c.Awardwinners(w1, w2, w3, id) {
                okAwards++;
            } catch {}
        } else if (mode == 1) {
            try c.AwardWithPercentage(w1, w2, w3, a % 101, b % 101, d % 101, id) {
                okAwards++;
            } catch {}
        } else {
            try c.Awardforfree_comp(
                w1, w2, w3, bound(a, 0, 10 ether), bound(b, 0, 10 ether), bound(d, 0, 10 ether), id
            ) {
                okAwards++;
            } catch {}
        }
    }

    function awardDuel(uint256 idSeed, uint256 playerSeed) external {
        if (ids.length == 0 || !_ready(_id(idSeed), playerSeed)) return;
        try c.Awardforduel_comp(payable(_player(playerSeed)), _id(idSeed)) {
            okAwards++;
        } catch {}
    }

    function awardArbitrary(uint256 idSeed, uint256 x, uint256 y) external {
        if (ids.length == 0 || !_ready(_id(idSeed), x)) return;
        address payable[] memory w = new address payable[](2);
        w[0] = payable(players[3]);
        w[1] = payable(players[4]);
        uint256[] memory amounts = new uint256[](2);
        amounts[0] = bound(x, 0, 30 ether);
        amounts[1] = bound(y, 0, 30 ether);
        try c.Awardforarbitrary_comp(w, amounts, _id(idSeed)) {
            okAwards++;
        } catch {}
    }

    function cancel(uint256 idSeed, uint256 seed) external {
        if (ids.length == 0 || !_ready(_id(idSeed), seed)) return;
        try c.cancelComp(_id(idSeed)) {
            okCancels++;
        } catch {}
    }

    function claimRefund(uint256 idSeed, uint256 playerSeed) external {
        if (ids.length == 0) return;
        uint256 id = _cancelledId(idSeed);
        vm.prank(_player(playerSeed));
        try c.claimRefund(id) {
            okRefunds++;
        } catch {}
    }

    function refundAll(uint256 idSeed) external {
        if (ids.length == 0) return;
        uint256 id = _cancelledId(idSeed);
        uint256 before = c.getcomp(id).participants;
        try c.refundParticipants(id, players) {
            okRefunds += before - c.getcomp(id).participants;
        } catch {}
    }

    function withdraw(uint256 idSeed) external {
        if (ids.length == 0) return;
        try c.withdrawOwner(payable(treasury), _id(idSeed)) {
            okWithdrawals++;
        } catch {}
    }

    function warp(uint256 secs) external {
        vm.warp(block.timestamp + bound(secs, 1, 3 days));
    }
}

contract ContestPrizeInvariantTest is Test {
    ContestPrize c;
    ContestPrizeHandler handler;

    function setUp() public {
        c = new ContestPrize();
        handler = new ContestPrizeHandler(c);
        c.transferOwnership(address(handler));
        targetContract(address(handler));
    }

    // every wei in the contract belongs to exactly one contest
    function invariant_balanceEqualsSumOfContestTotals() public view {
        uint256 sum;
        for (uint256 i = 0; i < handler.idsLength(); i++) {
            sum += c.getcomptotal(handler.ids(i));
        }
        assertEq(address(c).balance, sum);
    }

    function afterInvariant() public view {
        console.log("successful signups     ", handler.okSignups());
        console.log("successful awards      ", handler.okAwards());
        console.log("successful cancels     ", handler.okCancels());
        console.log("successful refunds     ", handler.okRefunds());
        console.log("successful withdrawals ", handler.okWithdrawals());
    }

    // a cancelled contest can always refund every remaining participant
    function invariant_cancelledContestsCoverRefunds() public view {
        for (uint256 i = 0; i < handler.idsLength(); i++) {
            ContestPrize.comp memory k = c.getcomp(handler.ids(i));
            if (k.cancelled) {
                assertGe(k.Total_amount, uint256(k.participants) * k.Price);
            }
            if (k.status) {
                assertFalse(k.cancelled);
            }
        }
    }
}
