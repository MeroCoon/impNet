import React, { useEffect, useState, createContext, useContext } from "react";
import "./App.css";
import "./components/Components.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import axios from "axios";
import DocumentsManager from "./components/DocumentsManager";
import PassportManager from "./components/PassportManager";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Context для управления темой
const ThemeContext = createContext();

// Context для управления аутентификацией
const AuthContext = createContext();

// Hook для использования темы
const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

// Hook для использования аутентификации
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Provider для темы
const ThemeProvider = ({ children }) => {
  const [isDark, setIsDark] = useState(true);

  const toggleTheme = () => {
    setIsDark(!isDark);
    localStorage.setItem('theme', !isDark ? 'dark' : 'light');
  };

  useEffect(() => {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
      setIsDark(savedTheme === 'dark');
    }
  }, []);

  return (
    <ThemeContext.Provider value={{ isDark, toggleTheme }}>
      <div className={isDark ? 'dark' : 'light'}>
        {children}
      </div>
    </ThemeContext.Provider>
  );
};

// Provider для аутентификации
const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchCurrentUser();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchCurrentUser = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setUser(response.data);
    } catch (error) {
      console.error('Error fetching current user:', error);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    try {
      const response = await axios.post(`${API}/auth/login`, { email, password });
      const { access_token, user: userData } = response.data;
      
      localStorage.setItem('token', access_token);
      setToken(access_token);
      setUser(userData);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      return { success: true };
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Login failed' 
      };
    }
  };

  const register = async (userData) => {
    try {
      const response = await axios.post(`${API}/auth/register`, userData);
      const { access_token, user: newUser } = response.data;
      
      localStorage.setItem('token', access_token);
      setToken(access_token);
      setUser(newUser);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      return { success: true };
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Registration failed' 
      };
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    delete axios.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

// Компонент переключения темы
const ThemeToggle = () => {
  const { isDark, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="theme-toggle"
      aria-label="Toggle theme"
    >
      {isDark ? (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="5"/>
          <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
        </svg>
      ) : (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>
      )}
    </button>
  );
};

// Компонент Header
const Header = () => {
  const { user, logout } = useAuth();

  return (
    <header className="header">
      <div className="header-content">
        <div className="logo">
          <h1>impNet</h1>
          <span className="logo-subtitle">Локальная сеть</span>
        </div>
        
        <nav className="nav">
          <a href="#dashboard" className="nav-link">Главная</a>
          <a href="#services" className="nav-link">Услуги</a>
          <a href="#documents" className="nav-link">Документы</a>
          <a href="#messages" className="nav-link">Сообщения</a>
        </nav>

        <div className="header-actions">
          <ThemeToggle />
          {user && (
            <div className="user-menu">
              <span className="user-name">{user.full_name}</span>
              <button onClick={logout} className="logout-btn">
                Выход
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

// Компонент формы входа
const LoginForm = () => {
  const { login } = useAuth();
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = await login(formData.email, formData.password);
    
    if (!result.success) {
      setError(result.error);
    }
    
    setLoading(false);
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <h2>Вход в impNet</h2>
          <p>Добро пожаловать в локальную сеть</p>
        </div>
        
        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
              placeholder="admin@impnet.ru"
            />
          </div>
          
          <div className="form-group">
            <label>Пароль</label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              required
              placeholder="••••••••"
            />
          </div>
          
          {error && <div className="error-message">{error}</div>}
          
          <button type="submit" disabled={loading} className="auth-button">
            {loading ? 'Вход...' : 'Войти'}
          </button>
        </form>
        
        <div className="auth-footer">
          <p>Тестовый аккаунт: admin@impnet.ru / admin123</p>
        </div>
      </div>
    </div>
  );
};

// Компонент Dashboard
const Dashboard = () => {
  const { user } = useAuth();
  const [roles, setRoles] = useState([]);

  useEffect(() => {
    fetchRoles();
  }, []);

  const fetchRoles = async () => {
    try {
      const response = await axios.get(`${API}/roles`);
      setRoles(response.data);
    } catch (error) {
      console.error('Error fetching roles:', error);
    }
  };

  const getUserRole = () => {
    return roles.find(role => role.id === user.role_id);
  };

  const userRole = getUserRole();

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Добро пожаловать, {user.full_name}!</h1>
        <p className="role-badge">
          {userRole?.display_name || 'Загружается...'}
        </p>
      </div>
      
      <div className="dashboard-grid">
        <div className="dashboard-card">
          <h3>Профиль</h3>
          <div className="profile-info">
            <p><strong>Email:</strong> {user.email}</p>
            <p><strong>Имя пользователя:</strong> {user.username}</p>
            <p><strong>Роль:</strong> {userRole?.display_name}</p>
            <p><strong>Создан:</strong> {new Date(user.created_at).toLocaleDateString()}</p>
          </div>
        </div>
        
        <div className="dashboard-card">
          <h3>Быстрые действия</h3>
          <div className="quick-actions">
            <button className="action-btn">📄 Документы</button>
            <button className="action-btn">🏛️ Услуги</button>
            <button className="action-btn">💬 Сообщения</button>
            <button className="action-btn">⭐ Рейтинг</button>
          </div>
        </div>
        
        <div className="dashboard-card">
          <h3>Уведомления</h3>
          <div className="notifications">
            <div className="notification">
              <div className="notification-icon">🔔</div>
              <div className="notification-content">
                <p>Добро пожаловать в impNet!</p>
                <span className="notification-time">Сейчас</span>
              </div>
            </div>
          </div>
        </div>
        
        <div className="dashboard-card">
          <h3>Системная информация</h3>
          <div className="system-info">
            <p><strong>Версия:</strong> impNet v1.0.0</p>
            <p><strong>Статус:</strong> <span className="status-online">Онлайн</span></p>
            <p><strong>Пользователей:</strong> {roles.length > 0 ? 'Активно' : 'Загружается...'}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

// Главный компонент приложения
const AppContent = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <p>Загрузка impNet...</p>
      </div>
    );
  }

  return (
    <div className="app-container">
      {user ? (
        <>
          <Header />
          <main className="main-content">
            <Dashboard />
          </main>
        </>
      ) : (
        <LoginForm />
      )}
    </div>
  );
};

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <div className="App">
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<AppContent />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </div>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;