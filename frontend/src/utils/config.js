import axios from 'axios';
import API_URL from './api';

function config() {
    
    var postobject = axios.create({
        baseURL: `${API_URL}/api`
    })
    
    postobject.interceptors.request.use(
        (config) => {
          const token = localStorage.getItem('token');
          if (token) {
            config.headers.Authorization = `Bearer ${token}`;
          }
          return config;
        },
        (error) => Promise.reject(error)
    );
    
    postobject.interceptors.response.use(
        (response) => response,
        async (error) => {
          const originalRequest = error.config;
          if (error.response.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;
      
            try {
              const refreshToken = localStorage.getItem('refreshToken');
              const response = await axios.post(`${API_URL}/api/token/refresh/`, {refresh: refreshToken} );
              const { access } = response.data;
              
              localStorage.setItem('token', access);
      
              // Retry the original request with the new token
              originalRequest.headers.Authorization = `Bearer ${access}`;
              return axios(originalRequest);
            } catch (error) {
              // Handle refresh token error or redirect to login
            }
          }
      
          return Promise.reject(error);
        }
    );

    return postobject;
}

export default config;