import React, { useEffect,useState } from 'react';
import axios from 'axios';
import Loader from "./Loader.js";
import config from '../utils/config.js';
import { Link } from "react-router-dom";
import API_URL from '../utils/api.js';


function CommentMiniProfile(props) {

    const {data} = props
    
    const [commentData, setcommentData] = useState([])
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        axios.get(data).then((res) => {
            setcommentData(res.data)
            setIsLoading(false)
        })
    }, [data])

    function deleteComment(CommentId) {

        const TokenConfig = config();

        TokenConfig.delete(`${API_URL}/api/comments/` + CommentId + "/delete/").then(response => {
            console.log('Resource deleted successfully:', response.data);
            alert("کامنت با موفقیت پاک شد");
            window.location.reload();
        }).catch(error => {
            console.error('Error deleting resource:', error);
            alert("کامنت پاک نشد! یه مشکلی وجود داره");
        })
    }

    if (isLoading) {
        return <Loader />
    } else {
        return (
            <div className="col-md-12 col-xs-12">
                <div className="comments-showing-accountPage">
                    <div className="col-md-1 col-xs-1">
                        <span className="comment-button" onClick={() => deleteComment(commentData.id)}><i className="fa fa-trash"></i></span>
                    </div>
                    <div className="col-xs-1  margin-mobile-responsive"></div>
                    <div className="col-md-11 col-xs-10">
                        <Link to={`/posts/${commentData.post}`}><h5>{commentData.content}</h5></Link>
                    </div>
                </div>
            </div>
        );
    }
}

export default CommentMiniProfile;