import { createContext, useContext, useState } from 'react';
import { login as apiLogin, register as apiRegister, getProfile } from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem('voxmentor_user');
      return stored ? JSON.parse(stored) : null;
    } catch { return null; }
  });
  const [loading] = useState(false);

  const login = async (email, password) => {
    const { data } = await apiLogin({ email, password });
    localStorage.setItem('voxmentor_token', data.token);
    localStorage.setItem('voxmentor_user', JSON.stringify(data));
    setUser(data);
    return data;
  };

  const register = async (formData) => {
    const { data } = await apiRegister(formData);
    localStorage.setItem('voxmentor_token', data.token);
    localStorage.setItem('voxmentor_user', JSON.stringify(data));
    setUser(data);
    return data;
  };

  const logout = () => {
    localStorage.removeItem('voxmentor_token');
    localStorage.removeItem('voxmentor_user');
    setUser(null);
  };

  const updateUser = (updated) => {
    localStorage.setItem('voxmentor_user', JSON.stringify(updated));
    setUser(updated);
  };

  const refreshUser = async () => {
    if (!user?.user_id) return;
    try {
      const { data } = await getProfile(user.user_id);
      const updated = { ...user, ...data };
      localStorage.setItem('voxmentor_user', JSON.stringify(updated));
      setUser(updated);
    } catch {
      // silently ignore profile refresh errors
    }
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, updateUser, refreshUser, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
