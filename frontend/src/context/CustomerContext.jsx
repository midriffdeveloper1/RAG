import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { identifyCustomer } from "../services/api.js";

const CustomerContext = createContext(null);

const STORAGE_KEY = "ai_support_agent_customer";

function readStored() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function CustomerProvider({ children }) {
  const [customer, setCustomer] = useState(() => readStored());
  const [lastGreeting, setLastGreeting] = useState(null); 

  useEffect(() => {
    if (customer) {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(customer));
    } else {
      sessionStorage.removeItem(STORAGE_KEY);
    }
  }, [customer]);

  const identify = useCallback(async (email) => {
    const result = await identifyCustomer(email);
    setCustomer(result.customer);
    setLastGreeting({ isReturning: result.is_returning });
    return result;
  }, []);

  const clearGreeting = useCallback(() => setLastGreeting(null), []);

  const updateLocalProfile = useCallback((partial) => {
    setCustomer((prev) => (prev ? { ...prev, ...partial } : prev));
  }, []);

  const switchAccount = useCallback(() => {
    setCustomer(null);
    setLastGreeting(null);
  }, []);

  return (
    <CustomerContext.Provider
      value={{
        customer,
        isIdentified: Boolean(customer),
        lastGreeting,
        clearGreeting,
        identify,
        updateLocalProfile,
        switchAccount,
      }}
    >
      {children}
    </CustomerContext.Provider>
  );
}

export function useCustomer() {
  const ctx = useContext(CustomerContext);
  if (!ctx) throw new Error("useCustomer must be used within CustomerProvider");
  return ctx;
}