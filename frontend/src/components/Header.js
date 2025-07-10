import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from 'axios';
import IsAuthenticated from "../utils/IsAuthenticated.js";
import logo from "../assets/images/MATHBOTrect.png"
import API_URL from '../utils/api.js';

function Header() {

    const [data, setdata] = useState([])

    useEffect(() => {
        if (IsAuthenticated() !== "Not Authenticated") {
            axios.get(`${API_URL}/api/accounts/` + IsAuthenticated()).then((res) => {
                setdata(res.data)
            })
        }
    }, [])

    function userData() {
        return (
            <>
                <Link title={data.name} to="/account">
                    <img src={data.avatar} className="account-user-img-little-header" alt={data.name} />
                </Link>

                <Link title="اعلانات" to="/notifications">
                    <div className="header-buttons">
                        <i class="fa-regular fa-bell header-buttons-ico"></i>
                    </div>
                </Link>
            </>
        )
    }

    return (
        <div className="header">
            <div className="row">

                <div className="col-md-3 header-responsive header-icons-box">
                    
                    {IsAuthenticated() !== "Not Authenticated" ? userData() : (
                        <Link to="/login">
                            <div className="header-buttons header-buttons-login">       
                                ورود
                            </div>
                        </Link>
                    )}

                    <Link title="پست جدید" to="/post/create">
                        <div className="header-buttons">
                            <i className="fas fa-plus header-buttons-ico"></i>
                        </div>
                    </Link>

                    <Link title="جستجو" to="/search">
                        <div className="header-buttons">
                            <i className="fas fa-search header-buttons-ico"></i>
                        </div>
                    </Link>

                    <Link title="صفحه اصلی" to="/">
                        <div className="header-buttons">
                            <i className="fa-solid fa-house header-buttons-ico"></i>
                        </div>
                    </Link>

                </div>

                <div className="col-md-5 header-responsive"></div>

                <div className="col-md-4">
                    <div className="logo-button">
                        <Link to="/">
                            <img className="logo-img" src={logo} alt="MATHBOT Logo" />
                        </Link>
                    </div>
                </div>
                
            </div>
        </div>
    );
}

export default Header;