import { createContext, useContext, useEffect, useState } from "react";
import { adminLogin, getCurrentAdmin } from "../services/adminApi.js";
import { ADMIN_TOKEN_STORAGE_KEY } from "../services/api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [admin, setAdmin] = useState(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);

  // On load, if a token is already stored, verify it's still valid.
  useEffect(() => {
    const token = localStorage.getItem(ADMIN_TOKEN_STORAGE_KEY);
    if (!token) {
      setIsCheckingSession(false);
      return;
    }

    getCurrentAdmin()
      .then(setAdmin)
      .catch(() => {
        localStorage.removeItem(ADMIN_TOKEN_STORAGE_KEY);
      })
      .finally(() => setIsCheckingSession(false));
  }, []);

  async function login(email, password) {
    const { access_token: token } = await adminLogin(email, password);
    localStorage.setItem(ADMIN_TOKEN_STORAGE_KEY, token);
    const me = await getCurrentAdmin();
    setAdmin(me);
    return me;
  }

  function logout() {
    localStorage.removeItem(ADMIN_TOKEN_STORAGE_KEY);
    setAdmin(null);
  }

  return (
    <AuthContext.Provider
      value={{ admin, isAuthenticated: Boolean(admin), isCheckingSession, login, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}