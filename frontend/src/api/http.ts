import axios from 'axios'

export const http = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    return Promise.reject(error)
  },
)
