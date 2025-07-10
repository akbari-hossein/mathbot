import React, { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet';
import Header from "../components/Header.js";
import Footer from "../components/Footer.js";
import { useParams } from "react-router-dom";
import axios from 'axios';
import Loader from "../components/Loader.js";
import PostPublicProfile from '../components/PostPublicProfile.js';
import API_URL from '../utils/api.js';

function Users() {

    const {username} = useParams();

    const [data, setdata] = useState([])
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        axios.get(`${API_URL}/api/accounts/` + username + "/").then((res) => {
            setdata(res.data);
            setIsLoading(false)
        })

    },[username])

    function SendPostsLink(){
        const fetchedData = []
        for (const link of data.posts){
            fetchedData.unshift(<PostPublicProfile data={link} />)
        }

        if (fetchedData.length === 0) {
            return (
                <div style={{textAlign: "center"}}>
                    <p>هیچ پستی توسط <span>{data.name}</span> ثبت نشده است</p>
                </div>
            )
        } else {
            return fetchedData
        }
    }

    if (isLoading) {
        return <Loader />;
    } else {
        return (
            <div>

                <Header />

                <Helmet>
                    <title>{data.name}</title>
                </Helmet>

                <div className="section">
                    <div className="container">
                        <div style={{marginTop: "50px"}} className="col-md-12 responsive-box">
                            <div className="account-user-img-box-large">
                                <img style={{width: "200px", height: "200px"}} src={data.avatar} className="account-user-img" alt={data.name} />
                            </div>
                            <div style={{textAlign: "center"}} className="forum-title">
                                <h3>{data.name} / {data.username}@</h3>
                                <h4>{data.bio}</h4>
                            </div>

                            {SendPostsLink()}

                        </div>

                    </div>
                </div>

                <Footer />

            </div>
        );
    }
}

export default Users;