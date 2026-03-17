import axios from "axios";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api",
  headers: {
    "Content-Type": "application/json",
  },
});

export const useApi = () => {
  const get = async <T>(url: string): Promise<T> => {
    const { data } = await client.get<T>(url);
    return data;
  };

  const post = async <T>(url: string, payload: unknown): Promise<T> => {
    const { data } = await client.post<T>(url, payload);
    return data;
  };

  return {
    get,
    post,
  };
};
