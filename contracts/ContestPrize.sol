// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "@openzeppelin/contracts/access/Ownable.sol";

contract ContestPrize is Ownable {

    constructor() Ownable(msg.sender) {}   

    struct comp {
        uint256 ID;
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

    modifier CheckSameId(uint id) {
        require(!Components[id].exist, "invalid ID");
        _;
    }

    event ContestCreated(uint ID, uint Price);

    event WinnersAwarded(uint ID, address first, address second, address third);

    // This function is used to define a contest and takes the ID and cost of participating in the contest.
    function Addcomp(uint _ID, uint _Price) external onlyOwner CheckSameId(_ID) {
        Components[_ID] = comp(_ID, 0, _Price, true , true);
        emit ContestCreated(_ID , _Price);
    }
    // This function is used to define a free contest 
    function Addfreecomp(uint _ID) external onlyOwner CheckSameId(_ID) {
        Components[_ID] = comp(_ID, 0,0, true , true);
        emit ContestCreated(_ID , 0);
    }

    //This function is for determining the total budget of a competition and get ID and The number of contestants
    function Deposit(uint _ID , uint _cnt) external payable CheckActive(_ID) onlyOwner() {
        Components[_ID].Total_amount += (Components[_ID].Price * _cnt);
    }

    // Divides the prizes of a competition among the winners with predetermined percentages
    function Awardwinners(address payable _first, address payable _second,address payable _Third,uint _ID ) external CheckActive(_ID) onlyOwner  {
        require(_first != address(0) && _second != address(0) && _Third != address(0), "Invalid address");
        require(Components[_ID].exist == true , "invalid ID");
        uint award = Components[_ID].Total_amount;
        _first.transfer((award * 30) / 100);
        _second.transfer((award * 20) / 100);
        _Third.transfer((award * 10) / 100);
        emit WinnersAwarded(_ID , _first , _second , _Third);

        Components[_ID].Total_amount -= (award * 60) / 100;
        Components[_ID].status = false;
    }

    // just for get ether
    receive() external payable{}

    // return total budget of a contest with get ID
    function getcomptotal(uint _ID) external view returns(uint){
        require(Components[_ID].exist == true , "invalid ID");
        return Components[_ID].Total_amount;
    }
    //  just return Running or finished competition
    function getcompstatus(uint _ID) external view returns(bool){
        require(Components[_ID].exist == true , "invalid ID");
        return Components[_ID].status;
    }
    // Checks whether or not there is a match with this ID.
    function getcompexist(uint _ID) external view returns(bool){
        return Components[_ID].exist;
    }

    // Distributes the prizes of a contest according to the percentage of entries.
    function AwardWithPercentage(address payable _first, address payable _second,address payable _Third , uint percent1 , uint percent2 , uint percent3 , uint _ID)external CheckActive(_ID) onlyOwner {
        uint sum = percent1 + percent2 + percent3;
        require(sum <= 100 , "Wrong percentages");
        require(Components[_ID].exist == true , "invalid ID");
        uint award = Components[_ID].Total_amount;
         _first.transfer((award * percent1) / 100);
        _second.transfer((award * percent2) / 100);
        _Third.transfer((award * percent3) / 100);
        Components[_ID].Total_amount -= (award * sum) / 100;
        Components[_ID].status = false;
    }
    // This function is for withdrawing the organizer's share of the prize after the competition ends.
    function withdrawOwner(address payable _to , uint _ID) external onlyOwner(){
        require(Components[_ID].status == false , "Components is not over");
        _to.transfer(Components[_ID].Total_amount);
    }
}
