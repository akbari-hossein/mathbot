// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Script.sol";
import "../src/ContestPrize.sol";

contract Deploycontestprize is Script {
    function setUp() public {}
    function run() public {
        vm.startBroadcast();
        new ContestPrize();
        vm.stopBroadcast();
    }
}