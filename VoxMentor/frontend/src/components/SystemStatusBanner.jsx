import { useEffect, useState } from 'react';
import { getSystemHealth } from '../api';

export default function SystemStatusBanner() {
  const [state, setState] = useState({ visible: false, message: '' });

  useEffect(() => {
    let alive = true;

    const check = async () => {
      try {
        const { data } = await getSystemHealth();
        const dbUp = data?.services?.database === 'up';
        const llmUp = data?.services?.llm === 'up';
        const provider = data?.llm_provider || 'llm';

        if (!dbUp) {
          if (alive) setState({ visible: true, message: 'Database is offline. Some features may not work.' });
          return;
        }

        if (!llmUp) {
          if (alive) setState({ visible: true, message: `${provider} is offline. AI tutor, challenge generation, and explanations are limited.` });
          return;
        }

        if (alive) setState({ visible: false, message: '' });
      } catch {
        if (alive) setState({ visible: true, message: 'Backend is offline. Start the API server (default port: 8000).' });
      }
    };

    check();
    const timer = setInterval(check, 15000);

    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, []);

  if (!state.visible) return null;

  return (
    <div className="system-status-banner" role="status" aria-live="polite">
      {state.message}
    </div>
  );
}
