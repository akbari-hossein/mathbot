import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Loader from "./Loader.js";
import Creator from './Creator.js';
import API_URL from '../utils/api.js';

function PostsListHomePage() {

    const [lisitng, setListing] = useState([]);
    const [fetchError, setfetchError] = useState(false);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await fetch(`${API_URL}/api/posts/?page=` + 1);
                const json = await response.json();
                setIsLoading(false);
                setListing(json.results);
            } catch {
                setfetchError(true)
            }
        };
      
        fetchData();
    },[])

    if (isLoading) {
        if (!fetchError) {
            return <Loader />
        } else {
            return (
                <div className="failedtofetch">
                    <span className="failedtofetch-icon"><i className="fa-solid fa-circle-exclamation"></i></span><p>عدم اتصال با سرور</p>
                </div>
            )
        }
    } else {
        return (
            <>
                {lisitng.map((data) =>
                    <div className="post-box">
                        <div className="row">
                            <div className="col-md-12">
                                <Creator data={data.creator} />
                            </div>
                        </div>
                        <Link className="post-box-link" to={`/posts/${data.id}`}>
                            <h4 className="post-title">{data.title}</h4>
                            {data.image != null ? (
                                <div className="post-img-box">
                                    <img loading="lazy" src={data.image} className="post-img" alt={data.title} />
                                </div>
                            ) : (
                                <div style={{marginBottom: "15px", lineHeight: "24px"}}>
                                    <span>{data.content}</span>
                                </div>
                            )}
                        </Link>
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
                    )
                }     
            </>
        );    
    }    
    
}

export default PostsListHomePage;