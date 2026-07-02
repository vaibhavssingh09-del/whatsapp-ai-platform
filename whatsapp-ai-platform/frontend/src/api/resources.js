import { apiClient } from "./client";

export const authApi = {
  login: (email, password) => apiClient.post("/auth/login", { email, password }).then((r) => r.data),
  me: () => apiClient.get("/auth/me").then((r) => r.data),
  switchTenant: (tenant_id) => apiClient.post("/auth/switch-tenant", { tenant_id }).then((r) => r.data),
};

export const tenantsApi = {
  accessible: () => apiClient.get("/tenants/accessible").then((r) => r.data),
  current: () => apiClient.get("/tenants/current").then((r) => r.data),
};

export const conversationsApi = {
  list: (statusFilter) =>
    apiClient.get("/conversations", { params: statusFilter ? { status_filter: statusFilter } : {} }).then((r) => r.data),
  messages: (conversationId) => apiClient.get(`/conversations/${conversationId}/messages`).then((r) => r.data),
  reply: (conversationId, text) => apiClient.post(`/conversations/${conversationId}/reply`, { text }).then((r) => r.data),
  resolve: (conversationId) => apiClient.post(`/conversations/${conversationId}/resolve`).then((r) => r.data),
};

export const mediaApi = {
  list: () => apiClient.get("/media").then((r) => r.data),
  upload: (file) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiClient.post("/media", formData, { headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data);
  },
  sendToConversation: (assetId, conversationId) =>
    apiClient.post(`/media/${assetId}/send/${conversationId}`).then((r) => r.data),
};

export const broadcastsApi = {
  list: () => apiClient.get("/broadcasts").then((r) => r.data),
  create: (payload) => apiClient.post("/broadcasts", payload).then((r) => r.data),
  get: (id) => apiClient.get(`/broadcasts/${id}`).then((r) => r.data),
};

export const dashboardApi = {
  metrics: () => apiClient.get("/dashboard/metrics").then((r) => r.data),
  auditLogs: () => apiClient.get("/dashboard/audit-logs").then((r) => r.data),
};
