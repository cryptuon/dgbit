import { createRouter, createWebHistory } from "vue-router";

const Dashboard = () => import("../pages/Dashboard.vue");
const Backtests = () => import("../pages/Backtests.vue");

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "dashboard", component: Dashboard },
    { path: "/backtests", name: "backtests", component: Backtests },
  ],
});

export default router;
