import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth context
const AuthContext = React.createContext();

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchCurrentUser();
    }
  }, [token]);

  const fetchCurrentUser = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setUser(response.data);
    } catch (error) {
      console.error('Error fetching user:', error);
      logout();
    }
  };

  const login = async (username, password) => {
    try {
      const response = await axios.post(`${API}/auth/login`, { username, password });
      const { access_token, user: userData } = response.data;
      setToken(access_token);
      setUser(userData);
      localStorage.setItem('token', access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      return { success: true };
    } catch (error) {
      return { success: false, error: error.response?.data?.detail || 'Login failed' };
    }
  };

  const register = async (userData) => {
    try {
      const response = await axios.post(`${API}/auth/register`, userData);
      return { success: true, user: response.data };
    } catch (error) {
      return { success: false, error: error.response?.data?.detail || 'Registration failed' };
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, token }}>
      {children}
    </AuthContext.Provider>
  );
};

const useAuth = () => {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Navigation component
const Navigation = () => {
  const { user, logout } = useAuth();
  const [currentView, setCurrentView] = useState('dashboard');

  return (
    <nav className="navigation">
      <div className="nav-header">
        <h1>🌐 ImpNet</h1>
        <div className="nav-user">
          <span className="balance">💰 {user?.balance?.toFixed(2)} Ǐ</span>
          <span className="username">{user?.username}</span>
          <button onClick={logout} className="logout-btn">Выход</button>
        </div>
      </div>
      <div className="nav-menu">
        <button 
          className={currentView === 'dashboard' ? 'active' : ''} 
          onClick={() => setCurrentView('dashboard')}
        >
          📊 Главная
        </button>
        <button 
          className={currentView === 'banking' ? 'active' : ''} 
          onClick={() => setCurrentView('banking')}
        >
          🏦 Банк
        </button>
        <button 
          className={currentView === 'chat' ? 'active' : ''} 
          onClick={() => setCurrentView('chat')}
        >
          💬 Чат
        </button>
        <button 
          className={currentView === 'email' ? 'active' : ''} 
          onClick={() => setCurrentView('email')}
        >
          📧 Почта
        </button>
        <button 
          className={currentView === 'files' ? 'active' : ''} 
          onClick={() => setCurrentView('files')}
        >
          📁 Файлы
        </button>
        <button 
          className={currentView === 'search' ? 'active' : ''} 
          onClick={() => setCurrentView('search')}
        >
          🔍 Поиск
        </button>
      </div>
      <MainContent currentView={currentView} />
    </nav>
  );
};

// Main content component
const MainContent = ({ currentView }) => {
  switch (currentView) {
    case 'dashboard':
      return <Dashboard />;
    case 'banking':
      return <Banking />;
    case 'chat':
      return <Chat />;
    case 'email':
      return <Email />;
    case 'files':
      return <Files />;
    case 'search':
      return <Search />;
    default:
      return <Dashboard />;
  }
};

// Dashboard component
const Dashboard = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState({});

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const [balanceRes, transactionsRes, messagesRes] = await Promise.all([
        axios.get(`${API}/banking/balance`),
        axios.get(`${API}/banking/transactions`),
        axios.get(`${API}/chat/messages`)
      ]);
      
      setStats({
        balance: balanceRes.data.balance,
        transactions: transactionsRes.data.length,
        messages: messagesRes.data.length
      });
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  return (
    <div className="dashboard">
      <div className="welcome-section">
        <h2>Добро пожаловать в ImpNet, {user?.full_name}!</h2>
        <p>Ваша автономная цифровая экосистема</p>
      </div>
      
      <div className="stats-grid">
        <div className="stat-card">
          <h3>💰 Баланс</h3>
          <p className="stat-value">{stats.balance?.toFixed(2)} Ǐ</p>
        </div>
        <div className="stat-card">
          <h3>🏦 Транзакций</h3>
          <p className="stat-value">{stats.transactions}</p>
        </div>
        <div className="stat-card">
          <h3>💬 Сообщений</h3>
          <p className="stat-value">{stats.messages}</p>
        </div>
        <div className="stat-card">
          <h3>📊 Статус</h3>
          <p className="stat-value">Активен</p>
        </div>
      </div>
      
      <div className="recent-activity">
        <h3>Последняя активность</h3>
        <div className="activity-list">
          <div className="activity-item">
            <span className="activity-icon">🏦</span>
            <span>Система активна и готова к использованию</span>
          </div>
          <div className="activity-item">
            <span className="activity-icon">💰</span>
            <span>Валюта Империум (Ǐ) доступна для операций</span>
          </div>
          <div className="activity-item">
            <span className="activity-icon">🌐</span>
            <span>Добро пожаловать в децентрализованную сеть</span>
          </div>
        </div>
      </div>
    </div>
  );
};

// Banking component
const Banking = () => {
  const [balance, setBalance] = useState(0);
  const [transactions, setTransactions] = useState([]);
  const [users, setUsers] = useState([]);
  const [transferData, setTransferData] = useState({
    to_user_id: '',
    amount: '',
    description: ''
  });

  useEffect(() => {
    fetchBankingData();
  }, []);

  const fetchBankingData = async () => {
    try {
      const [balanceRes, transactionsRes, usersRes] = await Promise.all([
        axios.get(`${API}/banking/balance`),
        axios.get(`${API}/banking/transactions`),
        axios.get(`${API}/banking/users`)
      ]);
      
      setBalance(balanceRes.data.balance);
      setTransactions(transactionsRes.data);
      setUsers(usersRes.data);
    } catch (error) {
      console.error('Error fetching banking data:', error);
    }
  };

  const handleTransfer = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/banking/transfer`, {
        to_user_id: transferData.to_user_id,
        amount: parseFloat(transferData.amount),
        description: transferData.description
      });
      
      setTransferData({ to_user_id: '', amount: '', description: '' });
      fetchBankingData();
      alert('Перевод выполнен успешно!');
    } catch (error) {
      alert('Ошибка при переводе: ' + (error.response?.data?.detail || error.message));
    }
  };

  return (
    <div className="banking">
      <div className="balance-section">
        <h2>💰 Баланс: {balance.toFixed(2)} Ǐ</h2>
        <p>Валюта Империум - официальная валюта ImpNet</p>
      </div>
      
      <div className="transfer-section">
        <h3>💸 Денежный перевод</h3>
        <form onSubmit={handleTransfer} className="transfer-form">
          <select 
            value={transferData.to_user_id} 
            onChange={(e) => setTransferData({...transferData, to_user_id: e.target.value})}
            required
          >
            <option value="">Выберите получателя</option>
            {users.map(user => (
              <option key={user.id} value={user.id}>
                {user.username} ({user.full_name})
              </option>
            ))}
          </select>
          <input
            type="number"
            step="0.01"
            placeholder="Сумма"
            value={transferData.amount}
            onChange={(e) => setTransferData({...transferData, amount: e.target.value})}
            required
          />
          <input
            type="text"
            placeholder="Описание"
            value={transferData.description}
            onChange={(e) => setTransferData({...transferData, description: e.target.value})}
            required
          />
          <button type="submit">Отправить перевод</button>
        </form>
      </div>
      
      <div className="transactions-section">
        <h3>📋 История транзакций</h3>
        <div className="transactions-list">
          {transactions.map(transaction => (
            <div key={transaction.id} className="transaction-item">
              <div className="transaction-info">
                <span className="transaction-type">
                  {transaction.transaction_type === 'salary' ? '💰' : '💸'}
                </span>
                <div className="transaction-details">
                  <p><strong>{transaction.description}</strong></p>
                  <p>Сумма: {transaction.amount} Ǐ</p>
                  <p>Дата: {new Date(transaction.created_at).toLocaleString()}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Chat component
const Chat = () => {
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchMessages();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchMessages = async () => {
    try {
      const response = await axios.get(`${API}/chat/messages`);
      setMessages(response.data.reverse());
    } catch (error) {
      console.error('Error fetching messages:', error);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim()) return;

    try {
      await axios.post(`${API}/chat/message`, {
        message: newMessage,
        message_type: 'text'
      });
      
      setNewMessage('');
      fetchMessages();
    } catch (error) {
      console.error('Error sending message:', error);
    }
  };

  return (
    <div className="chat">
      <div className="chat-header">
        <h2>💬 Общий чат ImpNet</h2>
        <p>Общайтесь с другими пользователями сети</p>
      </div>
      
      <div className="chat-messages">
        {messages.map(message => (
          <div key={message.id} className="message">
            <div className="message-header">
              <span className="message-author">{message.username}</span>
              <span className="message-time">
                {new Date(message.created_at).toLocaleTimeString()}
              </span>
            </div>
            <div className="message-content">{message.message}</div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      
      <form onSubmit={sendMessage} className="chat-input">
        <input
          type="text"
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
          placeholder="Введите сообщение..."
          maxLength={1000}
        />
        <button type="submit">Отправить</button>
      </form>
    </div>
  );
};

// Email component
const Email = () => {
  const [inbox, setInbox] = useState([]);
  const [sent, setSent] = useState([]);
  const [users, setUsers] = useState([]);
  const [currentView, setCurrentView] = useState('inbox');
  const [emailData, setEmailData] = useState({
    to_user_id: '',
    subject: '',
    body: ''
  });

  useEffect(() => {
    fetchEmailData();
  }, []);

  const fetchEmailData = async () => {
    try {
      const [inboxRes, sentRes, usersRes] = await Promise.all([
        axios.get(`${API}/email/inbox`),
        axios.get(`${API}/email/sent`),
        axios.get(`${API}/banking/users`)
      ]);
      
      setInbox(inboxRes.data);
      setSent(sentRes.data);
      setUsers(usersRes.data);
    } catch (error) {
      console.error('Error fetching email data:', error);
    }
  };

  const sendEmail = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/email/send`, emailData);
      setEmailData({ to_user_id: '', subject: '', body: '' });
      fetchEmailData();
      alert('Письмо отправлено!');
    } catch (error) {
      alert('Ошибка при отправке: ' + (error.response?.data?.detail || error.message));
    }
  };

  const markAsRead = async (emailId) => {
    try {
      await axios.put(`${API}/email/${emailId}/read`);
      fetchEmailData();
    } catch (error) {
      console.error('Error marking email as read:', error);
    }
  };

  return (
    <div className="email">
      <div className="email-header">
        <h2>📧 Почта ImpNet</h2>
        <div className="email-nav">
          <button 
            className={currentView === 'inbox' ? 'active' : ''}
            onClick={() => setCurrentView('inbox')}
          >
            📥 Входящие
          </button>
          <button 
            className={currentView === 'sent' ? 'active' : ''}
            onClick={() => setCurrentView('sent')}
          >
            📤 Отправленные
          </button>
          <button 
            className={currentView === 'compose' ? 'active' : ''}
            onClick={() => setCurrentView('compose')}
          >
            ✍️ Написать
          </button>
        </div>
      </div>
      
      {currentView === 'inbox' && (
        <div className="email-list">
          {inbox.map(email => (
            <div 
              key={email.id} 
              className={`email-item ${!email.is_read ? 'unread' : ''}`}
              onClick={() => markAsRead(email.id)}
            >
              <div className="email-info">
                <h4>{email.subject}</h4>
                <p>{email.body.substring(0, 100)}...</p>
                <small>{new Date(email.created_at).toLocaleString()}</small>
              </div>
            </div>
          ))}
        </div>
      )}
      
      {currentView === 'sent' && (
        <div className="email-list">
          {sent.map(email => (
            <div key={email.id} className="email-item">
              <div className="email-info">
                <h4>{email.subject}</h4>
                <p>{email.body.substring(0, 100)}...</p>
                <small>{new Date(email.created_at).toLocaleString()}</small>
              </div>
            </div>
          ))}
        </div>
      )}
      
      {currentView === 'compose' && (
        <form onSubmit={sendEmail} className="email-compose">
          <select 
            value={emailData.to_user_id} 
            onChange={(e) => setEmailData({...emailData, to_user_id: e.target.value})}
            required
          >
            <option value="">Выберите получателя</option>
            {users.map(user => (
              <option key={user.id} value={user.id}>
                {user.username} ({user.full_name})
              </option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Тема"
            value={emailData.subject}
            onChange={(e) => setEmailData({...emailData, subject: e.target.value})}
            required
          />
          <textarea
            placeholder="Текст сообщения"
            value={emailData.body}
            onChange={(e) => setEmailData({...emailData, body: e.target.value})}
            rows="10"
            required
          />
          <button type="submit">Отправить</button>
        </form>
      )}
    </div>
  );
};

// Files component
const Files = () => {
  const [files, setFiles] = useState([]);
  const [uploadData, setUploadData] = useState({
    filename: '',
    description: '',
    is_public: true
  });

  useEffect(() => {
    fetchFiles();
  }, []);

  const fetchFiles = async () => {
    try {
      const response = await axios.get(`${API}/files/list`);
      setFiles(response.data);
    } catch (error) {
      console.error('Error fetching files:', error);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (e) => {
      const base64Data = e.target.result.split(',')[1];
      
      try {
        await axios.post(`${API}/files/upload`, {
          filename: file.name,
          file_data: base64Data,
          file_type: file.type,
          file_size: file.size,
          description: uploadData.description,
          is_public: uploadData.is_public
        });
        
        fetchFiles();
        setUploadData({ filename: '', description: '', is_public: true });
        alert('Файл загружен успешно!');
      } catch (error) {
        alert('Ошибка при загрузке файла: ' + (error.response?.data?.detail || error.message));
      }
    };
    
    reader.readAsDataURL(file);
  };

  return (
    <div className="files">
      <div className="files-header">
        <h2>📁 Файловая система ImpNet</h2>
        <p>Делитесь файлами с другими пользователями</p>
      </div>
      
      <div className="file-upload">
        <h3>📤 Загрузить файл</h3>
        <input
          type="file"
          onChange={handleFileUpload}
          accept="*/*"
        />
        <input
          type="text"
          placeholder="Описание файла"
          value={uploadData.description}
          onChange={(e) => setUploadData({...uploadData, description: e.target.value})}
        />
        <label>
          <input
            type="checkbox"
            checked={uploadData.is_public}
            onChange={(e) => setUploadData({...uploadData, is_public: e.target.checked})}
          />
          Публичный доступ
        </label>
      </div>
      
      <div className="files-list">
        <h3>📋 Доступные файлы</h3>
        {files.map(file => (
          <div key={file.id} className="file-item">
            <div className="file-info">
              <h4>📄 {file.filename}</h4>
              <p>{file.description}</p>
              <small>
                Размер: {(file.file_size / 1024).toFixed(2)} KB | 
                Загружен: {new Date(file.created_at).toLocaleString()}
              </small>
            </div>
            <div className="file-actions">
              <a
                href={`data:${file.file_type};base64,${file.file_data}`}
                download={file.filename}
                className="download-btn"
              >
                ⬇️ Скачать
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Search component
const Search = () => {
  const [query, setQuery] = useState('');
  const [searchType, setSearchType] = useState('all');
  const [results, setResults] = useState({ messages: [], files: [], users: [] });

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    try {
      const response = await axios.post(`${API}/search`, {
        query: query,
        search_type: searchType
      });
      setResults(response.data);
    } catch (error) {
      console.error('Error searching:', error);
    }
  };

  return (
    <div className="search">
      <div className="search-header">
        <h2>🔍 Поиск по ImpNet</h2>
        <p>Найдите сообщения, файлы и пользователей</p>
      </div>
      
      <form onSubmit={handleSearch} className="search-form">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Введите поисковый запрос..."
        />
        <select 
          value={searchType} 
          onChange={(e) => setSearchType(e.target.value)}
        >
          <option value="all">Все</option>
          <option value="messages">Сообщения</option>
          <option value="files">Файлы</option>
          <option value="users">Пользователи</option>
        </select>
        <button type="submit">Поиск</button>
      </form>
      
      <div className="search-results">
        {results.messages.length > 0 && (
          <div className="result-section">
            <h3>💬 Сообщения</h3>
            {results.messages.map(message => (
              <div key={message.id} className="result-item">
                <p><strong>{message.username}:</strong> {message.message}</p>
                <small>{new Date(message.created_at).toLocaleString()}</small>
              </div>
            ))}
          </div>
        )}
        
        {results.files.length > 0 && (
          <div className="result-section">
            <h3>📁 Файлы</h3>
            {results.files.map(file => (
              <div key={file.id} className="result-item">
                <p><strong>{file.filename}</strong></p>
                <p>{file.description}</p>
                <small>{new Date(file.created_at).toLocaleString()}</small>
              </div>
            ))}
          </div>
        )}
        
        {results.users.length > 0 && (
          <div className="result-section">
            <h3>👥 Пользователи</h3>
            {results.users.map(user => (
              <div key={user.id} className="result-item">
                <p><strong>{user.username}</strong> ({user.full_name})</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// Login component
const Login = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    email: '',
    full_name: ''
  });
  const [error, setError] = useState('');
  const { login, register } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (isLogin) {
      const result = await login(formData.username, formData.password);
      if (!result.success) {
        setError(result.error);
      }
    } else {
      const result = await register(formData);
      if (result.success) {
        alert('Регистрация успешна! Теперь войдите в систему.');
        setIsLogin(true);
      } else {
        setError(result.error);
      }
    }
  };

  return (
    <div className="login-container">
      <div className="login-form">
        <h1>🌐 ImpNet</h1>
        <p>Добро пожаловать в автономную цифровую экосистему</p>
        
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Имя пользователя"
            value={formData.username}
            onChange={(e) => setFormData({...formData, username: e.target.value})}
            required
          />
          <input
            type="password"
            placeholder="Пароль"
            value={formData.password}
            onChange={(e) => setFormData({...formData, password: e.target.value})}
            required
          />
          
          {!isLogin && (
            <>
              <input
                type="email"
                placeholder="Email"
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                required
              />
              <input
                type="text"
                placeholder="Полное имя"
                value={formData.full_name}
                onChange={(e) => setFormData({...formData, full_name: e.target.value})}
                required
              />
            </>
          )}
          
          {error && <div className="error">{error}</div>}
          
          <button type="submit">
            {isLogin ? 'Войти' : 'Регистрация'}
          </button>
        </form>
        
        <p>
          {isLogin ? 'Нет аккаунта?' : 'Уже есть аккаунт?'}
          <button 
            type="button"
            onClick={() => setIsLogin(!isLogin)}
            className="link-button"
          >
            {isLogin ? 'Регистрация' : 'Войти'}
          </button>
        </p>
      </div>
    </div>
  );
};

// Main App component
function App() {
  return (
    <AuthProvider>
      <div className="App">
        <MainApp />
      </div>
    </AuthProvider>
  );
}

const MainApp = () => {
  const { user } = useAuth();

  if (!user) {
    return <Login />;
  }

  return <Navigation />;
};

export default App;