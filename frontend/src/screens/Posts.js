import React, { useEffect, useState } from 'react';
import Comment from '../components/Comment.js';
import { useParams , Link } from "react-router-dom";
import { Helmet } from 'react-helmet';
import Header from "../components/Header.js";
import Footer from "../components/Footer.js";
import axios from 'axios';
import UploadComment from '../components/UploadComment.js';
import Loader from "../components/Loader.js";
import LeftSidebar from "../components/LeftSidebar.js";
import Creator from '../components/Creator.js';
import API_URL from '../utils/api.js';

function Posts() {

    const {id} = useParams();    

    const [data, setdata] = useState([])
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
            axios.get(`${API_URL}/api/posts/` + id + "/").then((res) => {
                setdata(res.data);
                setIsLoading(false)
            })

    },[id])

    function SendCommentsLink(){

        let fetchedData = []

        for (const link of data.comments){

            fetchedData.unshift(<Comment data={link} />)
        }

        if (fetchedData.length === 0) {
            return (
                <></>
            )
        } else {
            return fetchedData
        }
    }

    return (
        <div>

            <Header />

            {isLoading ? <Loader /> : (

                <>
                    <Helmet>
                        <title>{data.title}</title>
                    </Helmet>

                    <div className="section">
                        <div className="container">
                            <div className="col-md-12 responsive-box">

                            <div className="col-md-3 responsive-box">
                                <LeftSidebar />
                            </div>

                            <div className="col-md-9 col-xs-12 responsive-box">
                                <div className="post-box-big">
                                    <div className="forum-title-postBox">
                                    <div className="row">
                                        <div className="col-md-12">
                                            <Creator data={data.creator} />
                                        </div>
                                    </div>
                                        <h4 className='post-title'>{data.title}</h4>
                                        {/* <div className="row post-box-big-details">
                                            <Link className="username-answer" to={`/users/${creator.username}`}>
                                                <div className="col-md-4 col-sm-4 col-xs-4 forum-title-ask">
                                                    <div className="account-user-img-box">
                                                        <img src={creator.avatar} className="account-user-img-little" alt={creator.name} />
                                                    </div>
                                                    <h6>{creator.name}</h6>
                                                </div>
                                            </Link>
                                            <div className="col-md-4 col-sm-4 col-xs-4 forum-title-view">
                                                <h6>{data.created_at}</h6>
                                            </div>
                                            <div className="col-md-4 col-sm-4 col-xs-4 forum-title-last-seen">
                                                <h6>{data.comments.length} <i class="fa-regular fa-comments"></i></h6>
                                            </div>
                                        </div> */}
                                    </div>

                                    {data.image != null ? (
                                        <div className="post-img-box">
                                            <img src={data.image} className="post-img" alt={data.title} />
                                        </div>
                                    ) : (<></>)}
                                    
                                    <div className="post-content-box">
                                        <p>{data.content}</p>
                                    </div>

                                    <div className='post-created-at'>
                                        <span>{data.created_at}</span>
                                    </div>

                                    <div className="row post-box-bottom">
                                        <div className="col-md-8 col-xs-8">
                                            {data.tags.split(",").map((e) => (
                                                <div className="post-tags">{e}</div>
                                            ))}
                                        </div>
                                        <div className="col-md-4 col-xs-s">
                                            <p className="post-answer">{data.comments.length} <i class="fa-regular fa-comments"></i></p>
                                        </div>
                                    </div>
                                </div>

                                <UploadComment postId={id} />

                                <div className="forum-title-posts">
                                    <h4>دیدگاه ها</h4>
                                </div>

                                {SendCommentsLink()}

                            </div>

                        </div>

                        </div>
                    </div>
                </>

            )}

            <Footer />

        </div>
    )
}

export default Posts;