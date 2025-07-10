import React, { useState } from 'react';
import axios from 'axios';
import { Helmet } from 'react-helmet';
import Header from "../components/Header.js";
import { Link } from "react-router-dom";
import API_URL from '../utils/api.js';

function Register() {

    const [formData, setFormData] = useState({
        username: "",
        name: "",
        email: "",
        password: "",
      });
    
      // Function to handle form input changes
      const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
      };
    
      // Function to submit the form data using Axios
      const handleSubmit = async (e) => {
        e.preventDefault();
        try {
          const response = await axios.post(`${API_URL}/api/accounts/register/`, formData);
          console.log("Post created:", response.data);
          alert("اکانت با موفقیت ساخته شد");
          window.location.replace("/login");
        } catch (error) {
          var values = Object.values(error.response.data)
          var keys = Object.keys(error.response.data)
          const errors = []
          for (let index = 0; index < values.length; index++) {
            for (let indexd = 0; indexd < keys.length; indexd++) {
                if (index === indexd) {
                    errors.push("\n" + values[index] + " " + keys[indexd])
                }              
            }
          }
          alert(errors)
        }
      };

    return (
        <div>

            <Header />

            <Helmet>
                <title>Register</title>
            </Helmet>

            <div className="section">
                <div className="container-login">
                    <div className="login-page">
                        <div className="form">

                            <form className="register-form" onSubmit={handleSubmit}>

                                <h4 style={{marginBottom: "25px"}}>ثبت نام در سایت</h4>

                                <input
                                    required
                                    type="text"
                                    label="Name"
                                    name="name"
                                    maxlength="32"
                                    placeholder= "* نام و نام خانوادگی"
                                    value={formData.name}
                                    onChange={handleChange}
                                />

                                <input
                                    required
                                    type="text"
                                    label="Username"
                                    name="username"
                                    maxlength="32"
                                    placeholder="* نام کاربری (حداقل ۴ کاراکتر)"
                                    value={formData.username}
                                    onChange={handleChange}
                                />

                                <input
                                    required
                                    type="email"
                                    label="Email"
                                    name="email"
                                    placeholder="* ایمیل"
                                    value={formData.email}
                                    onChange={handleChange}
                                />

                                <input
                                    required
                                    type="password"
                                    label="Password"
                                    name="password"
                                    maxlength="32"
                                    placeholder="* پسورد (حداقل ۴ کاراکتر)"
                                    value={formData.password}
                                    onChange={handleChange}
                                />

                                {/* <div className="row terms">
                                    <div className="col-md-8">
                                        <span>شرایط و قوانین را قبول دارم</span>
                                    </div>
                                    <div className="col-md-4">
                                        <input
                                            inline
                                            required
                                            type="checkbox"
                                            name="agreement"
                                            checked={this.state.checked}
                                            onChange={this.handleCheckbox}
                                        />
                                    </div>
                                </div> */}
                                
                                <button type="submit">ثبت نام</button>

                                <p className="message">قبلا ثبت نام کرده اید؟ <Link to="/login">وارد شوید</Link></p>
                                
                            </form>

                        </div>
                    </div>
                </div>
            </div>
            
        </div>
    );
}

export default Register;