import { defineStore } from "pinia";
import { ref } from "vue";

import { useApi } from "../composables/useApi";

const api = useApi();

export interface Job {
  id: string;
  type: string;
  status: string;
  created_at: string;
  payload: Record<string, unknown>;
}

export interface Health {
  status: string;
  environment: string;
  service: string;
}

export const useJobsStore = defineStore("jobs", () => {
  const jobs = ref<Job[]>([]);
  const health = ref<Health>({
    status: "unknown",
    environment: "local",
    service: "dgbit-api",
  });

  const refreshHealth = async () => {
    const response = await api.get<Health>("/health");
    health.value = response;
  };

  const fetchJobs = async () => {
    const response = await api.get<Job[]>("/jobs");
    jobs.value = response;
  };

  const scheduleBacktest = async (payload: Record<string, unknown>) => {
    await api.post("/backtests", payload);
    await fetchJobs();
  };

  return {
    jobs,
    health,
    refreshHealth,
    fetchJobs,
    scheduleBacktest,
  };
});
