import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { authApi } from "../api/resources";
import { registerUnauthorizedHandler } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setUser(null);
  }, []);

  useEffect(() => {
    registerUnauthorizedHandler(logout);
  }, [logout]);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setIsLoading(false);
      return;
    }
    authApi
      .me()
      .then(setUser)
      .catch(() => logout())
      .finally(() => setIsLoading(false));
  }, [logout]);

  const login = async (email, password) => {
    const data = await authApi.login(email, password);
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    setUser(data.user);
    return data.user;
  };

  const switchTenant = async (tenantId) => {
    const data = await authApi.switchTenant(tenantId);
    localStorage.setItem("access_token", data.access_token);
    const refreshedUser = await authApi.me();
    setUser(refreshedUser);
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, switchTenant }}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
