import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { WelcomeView } from './components/views/WelcomeView';
import { ChatView } from './components/views/ChatView';
import { AdminView } from './components/views/AdminView';
import { SettingsView } from './components/views/SettingsView';
import { ErrorBoundary } from './components/ErrorBoundary';

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<WelcomeView />} />
            <Route path="chat" element={<ChatView />} />
            <Route path="admin" element={<AdminView />} />
            <Route path="settings" element={<SettingsView />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
