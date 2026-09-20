// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import "forge-std/Script.sol";
import "../src/ContestPrize.sol";

// Deploys ContestPrize.
//
//   forge script script/ContestPrize.s.sol:Deploycontestprize --rpc-url sepolia --broadcast --verify
//
// Signer: PRIVATE_KEY from .env if it is set, otherwise the signer given on the command line
// (e.g. `--account deployer` for a keystore made with `cast wallet import deployer --interactive`).
// CONTRACT_OWNER (optional): address that receives ownership after the deploy. Set it to the
// backend wallet (BLOCKCHAIN_OWNER_PRIVATE_KEY in backend/.env) when the deployer is a different key.
contract Deploycontestprize is Script {
    ContestPrize mycontract;

    function setUp() public {}

    function run() public returns (ContestPrize) {
        uint256 key = vm.envOr("PRIVATE_KEY", uint256(0));
        address newOwner = vm.envOr("CONTRACT_OWNER", address(0));

        if (key != 0) {
            vm.startBroadcast(key);
        } else {
            vm.startBroadcast();
        }
        mycontract = new ContestPrize();
        if (newOwner != address(0) && newOwner != mycontract.owner()) {
            mycontract.transferOwnership(newOwner);
        }
        vm.stopBroadcast();

        console.log("ContestPrize deployed at:", address(mycontract));
        console.log("chain id:", block.chainid);
        console.log("owner:", mycontract.owner());
        return mycontract;
    }
}
