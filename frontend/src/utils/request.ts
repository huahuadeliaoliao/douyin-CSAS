import axios from 'axios'

const request = axios.create({
  baseURL: 'http://localhost:8713',
})

export default request
