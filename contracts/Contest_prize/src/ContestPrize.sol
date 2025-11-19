// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";


contract ContestPrize is Ownable, ReentrancyGuard, Pausable {
    constructor() Ownable(msg.sender) {}

    struct comp {
        uint256 Total_amount;
        uint256 Price;
        bool status;
        bool exist;
    }
    // for save each contest wtih ID
    mapping(uint => comp) Components;

    modifier CheckActive(uint id) {
        require(Components[id].status == true, "component finished");
        _;
    }

    modifier ChecknotexistId(uint id) {
        require(!Components[id].exist, "this ID is already exist");
        _;
    }
    modifier CheckexistID(uint id) {
        require(Components[id].exist, "this ID is not exist");
        _;
    }
    // Error for wrong percentage inputs
    error wrongpercentage(uint);
    // Error for wrong address inputs
    error wrongaddress(address first , address second , address third);

    event ContestCreated(uint256 ID, uint256 Price);

    event WinnersAwarded(uint256 ID, address first, address second, address third);

    event signupcompleted(uint256 indexed ID, address indexed user);

    // This function is used to define a contest and takes the ID and cost of participating in the contest.
    function Addcomp(
        uint256 _ID,
        uint256 _Price , uint256 _totalprize
    ) external onlyOwner ChecknotexistId(_ID) whenNotPaused {
        if (_Price == 0 ){
            Components[_ID] = comp(_totalprize, 0, true, true);
        }
        else {
            Components[_ID] = comp(0, _Price, true, true);
        }
        emit ContestCreated(_ID, _Price);
    }

    // this function is for user signup in a contest user should call 
    function signup(uint256 _ID) external payable CheckexistID(_ID) CheckActive(_ID) whenNotPaused{
    uint256 price = Components[_ID].Price;
    require(msg.value == price, "Incorrect ETH amount");

    Components[_ID].Total_amount += msg.value;

    emit signupcompleted(_ID, msg.sender);
    }
    // owner should call this if the contest is free
    function addbudgeforfreecomp(uint256 _ID) external payable onlyOwner CheckexistID(_ID) whenNotPaused {
        require(msg.value == Components[_ID].Total_amount, "Must send ETH");
    }

    // Internal function to safely transfer Ether
    function _safetransfer(address payable recipient, uint256 amount) internal {
        (bool success,) = recipient.call{value: amount}("");
        require(success, "Transfer failed");
    }
    
    // Divides the prizes of a competition among the winners with predetermined percentages
    function Awardwinners(
        address payable _first,
        address payable _second,
        address payable _Third,
        uint256 _ID
    ) external onlyOwner CheckexistID(_ID) CheckActive(_ID) nonReentrant whenNotPaused {
        if (_first == address(0) || _second == address(0) || _Third == address(0)) {
            revert wrongaddress(_first, _second, _Third);
        }
        uint256 award = Components[_ID].Total_amount; 
        Components[_ID].status = false;
        _safetransfer(_first, (award * 30) / 100);
        Components[_ID].Total_amount -= (30 * award) / 100 ;
        _safetransfer(_second, (award * 20) / 100);
        Components[_ID].Total_amount -= (20 * award) / 100 ;
        _safetransfer(_Third, (award * 10) / 100);
        Components[_ID].Total_amount -= (10 * award) / 100 ;
        emit WinnersAwarded(_ID, _first, _second, _Third);
    }

    // just for get ether
    receive() external payable {}

    // Distributes the prizes of a contest according to the percentage of entries.
    function AwardWithPercentage(
        address payable _first,
        address payable _second,
        address payable _Third,
        uint256 percent1,
        uint256 percent2,
        uint256 percent3,
        uint256 _ID
    ) external onlyOwner CheckexistID(_ID) CheckActive(_ID) nonReentrant whenNotPaused {
        if (_first == address(0) || _second == address(0) || _Third == address(0)) {
            revert wrongaddress(_first, _second, _Third);
        }
        uint256 sum = percent1 + percent2 + percent3;
        if (sum > 100) revert wrongpercentage(sum);
        Components[_ID].status = false;
        uint256 award = Components[_ID].Total_amount;
        _safetransfer(_first, (award * percent1) / 100);
        Components[_ID].Total_amount -= (percent1 * award) / 100 ;
        _safetransfer(_second, (award * percent2) / 100);
        Components[_ID].Total_amount -= (percent2 * award) / 100 ;
        _safetransfer(_Third, (award * percent3) / 100);
        Components[_ID].Total_amount -= (percent3 * award) / 100 ;
    }

    // function for freecomp and 3 person winner get: It takes the addresses of the
    //top 3 people and the amount of Ethereum awarded to each of them and distributes the prizes.
    function Awardforfree_comp(
        address payable _first,
        address payable _second,
        address payable _Third,
        uint256 value_first,
        uint256 value_second,
        uint256 value_Third,
        uint256 ID
    ) external onlyOwner CheckexistID(ID) CheckActive(ID) nonReentrant whenNotPaused {
        if (_first == address(0) || _second == address(0) || _Third == address(0)) {
            revert wrongaddress(_first, _second, _Third);
        }
        Components[ID].status = false;
        _safetransfer(_first, value_first);
        Components[ID].Total_amount -= value_first;
        _safetransfer(_second, value_second);
        Components[ID].Total_amount -= value_second;
        _safetransfer(_Third, value_Third);
        Components[ID].Total_amount -= value_Third;
    }

    // this function Get the winner's address and ID for the duel competition and give her the prize for the duel competition.
    function Awardforduel_comp(
        address payable _first,
        uint256 ID_comp
    )
        external
        onlyOwner CheckexistID(ID_comp)
        CheckActive(ID_comp)
        nonReentrant
        whenNotPaused
    {
        require(_first != address(0), "Invalid address");
        Components[ID_comp].status = false;
        // 90% of the total amount is given to the winner
        uint value = (Components[ID_comp].Total_amount * 90) / 100;
        _safetransfer(_first, value);
        unchecked {
            Components[ID_comp].Total_amount -= value;
        }
    }

    // Prize distribution for competitions with arbitrary prizes Each person
    // takes a presentation of the winners and a presentation of the prizes and distributes the prizes.
    // prize = amount ether
    function Awardforarbitrary_comp(
        address payable[] calldata winners,
        uint256[] calldata prize,
        uint256 ID
    ) external onlyOwner CheckexistID(ID) CheckActive(ID) nonReentrant whenNotPaused {
        require(winners.length == prize.length && winners.length > 0, "Length mismatch");
        Components[ID].status = false;
        for (uint256 i = 0; i < winners.length; i++) {
            require(winners[i] != address(0), "invalid address");
            _safetransfer(winners[i], prize[i]);
            unchecked {
                Components[ID].Total_amount -= prize[i];
            }
        }
    }

    // This function is for withdrawing the organizer's share of the prize after the competition ends.
    function withdrawOwner(
        address payable _to,
        uint256 _ID
    ) external onlyOwner CheckexistID(_ID) nonReentrant whenNotPaused {
        require(Components[_ID].status == false, "Components is not over");
        uint256 amount = Components[_ID].Total_amount;
        Components[_ID].Total_amount = 0;
        _safetransfer(_to, amount);
    }

    // return total budget of a contest with get ID
    function getcomptotal(
        uint256 _ID
    ) external view CheckexistID(_ID) returns (uint256) {
        return Components[_ID].Total_amount;
    }

    //  just return Running or finished competition
    function getcompstatus(
        uint256 _ID
    ) external view CheckexistID(_ID) returns (bool) {
        return Components[_ID].status;
    }

    // Checks whether or not there is a match with this ID.
    function getcompexist(uint256 _ID) external view returns (bool) {
        return Components[_ID].exist;
    }
    // if contract We encountered a problem, contract owner can stop the work
    function pause() external onlyOwner {
        _pause();
    }
    // if contract is paused, no one can enter the competition
    function unpause() external onlyOwner {
        _unpause();
    }
}
