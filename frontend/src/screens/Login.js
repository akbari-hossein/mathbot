import React, { useState } from 'react';
import axios from 'axios';
import { Helmet } from 'react-helmet';
import Header from "../components/Header.js";
import { Link } from "react-router-dom";
import API_URL from '../utils/api.js';

function Login() {
    
    const [credentials, setCredentials] = useState({
        username: '',
        password: ''
      });
    
      const handleChange = (e) => {
        setCredentials({
          ...credentials,
          [e.target.name]: e.target.value
        });
      };
    
      const handleSubmit = async (e) => {
        e.preventDefault();
    
        try {
          const response = await axios.post(`${API_URL}/api/token/`, credentials);
          const { access, refresh } = response.data;
    
          // Store the tokens in localStorage or secure cookie for later use
          localStorage.setItem('token', access);
          localStorage.setItem('refreshToken', refresh);

          window.location.replace("/account");
        } catch {
            alert("نام کاربری یا رمز عبور اشتباه وارد شده است")
        }
      };
    
        
    return (
        <div>

            <Header />

            <Helmet>
                <title>Login</title>
            </Helmet>

            <div className="section">
                <div className="container-login">
                    <div className="login-page">
                        <div className="form">

                            <form className="login-form" onSubmit={handleSubmit}>

                                <h4 style={{marginBottom: "25px"}}>ورود به حساب کاربری</h4>

                                <input
                                    required
                                    type="text"
                                    label="Username"
                                    name="username"
                                    placeholder="نام کاربری"
                                    value={credentials.email}
                                    onChange={handleChange}
                                />

                                <input
                                    required
                                    type="password"
                                    label="Password"
                                    name="password"
                                    placeholder="پسورد"
                                    value={credentials.password}
                                    onChange={handleChange}
                                />

                                <button type="submit">ورود</button>

                                <p className="message">هنوز ثبت نام نکرده اید؟ <Link to="/register">یک اکانت بسازید</Link></p>

                            </form>

                        </div>
                    </div>
                </div>
            </div>
            
        </div>
    );
    
}

export default Login;