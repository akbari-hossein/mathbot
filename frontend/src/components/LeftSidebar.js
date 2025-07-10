import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import IsAuthenticated from "../utils/IsAuthenticated.js";
import axios from 'axios';
import API_URL from '../utils/api.js';

function LeftSidebar() {

    const username = IsAuthenticated()
    const [data, setdata] = useState([])

    useEffect(() => {
        if (IsAuthenticated() !== "Not Authenticated") {
            axios.get(`${API_URL}/api/accounts/` + IsAuthenticated()).then((res) => {
                setdata(res.data)
            })
        }
    }, [])
    
    return (
        <>
            {username === "Not Authenticated" ? (
                <Link to="/login">
                    <div className="sidebar login-text-green">
                        <p>برای شرکت در مسابقات و فعالیت در انجمن وارد حساب کاربری خود شوید</p>
                    </div>
                </Link>
            ) : (
                <div className="sidebar">

                    <div className="user-data-sidebar">
                        <Link className="sidebar-user-links" to={`/users/${username}`}>
                            <div>
                                <img src={data.avatar} className="account-user-img" alt={data.name} />
                                <h4>{data.name}</h4>
                            </div>
                        </Link>
                        <h5>{data.bio}</h5>
                    </div>
                    <Link className="sidebar-user-links" to="/soon"><p><i class="fa-regular fa-bookmark"></i> ذخیره</p></Link>
                </div>
            )}
            <div className="sidebar">
                <p style={{textAlign: "left"}}>Ranking <i style={{color: "#29a58d"}}  class="fa-solid fa-fire"></i></p>
            </div>
            <div className="sidebar">
                <h5 className="upcoming-contest-sidebar">مسابقات پیش رو</h5>
                <Link className="sidebar-user-links" to="/soon">
                    <div className="contest-sidebar-box">
                        <div className="contest-sidebar-title">
                            <p>
                                مسابقه هفتگی مث بات دوره اول
                            </p>
                        </div>
                        <div>
                            <p>
                                تاریخ برگزاری: ۳ مهر ۱۴۰۳ ساعت ۲۲:۳۰
                            </p>
                            <p>
                                1532 شرکت کننده
                            </p>
                        </div>
                    </div>
                </Link>
            </div>
            <div className="sidebar contact-links">
                <a className="contact-icons-sidebar" href="http://instagram.com/themathbot "><i className="fab fa-instagram "></i></a>
                <a className="contact-icons-sidebar" href="http://t.me/math_20_bot_channel "><i className="fab fa-telegram "></i></a>
                <a className="contact-icons-sidebar" href="http://github.com/hosseincodes/mathbot "><i className="fab fa-github "></i></a>
            </div>
        </>
    );
}

export default LeftSidebar;