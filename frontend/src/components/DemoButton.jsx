import React, { useState, useRef, useCallback } from 'react';
import { api } from '../api/client';

const DEMO_STEPS = [
  { key: 'seed', label: 'Seeding demo data' },
  { key: 'schedule', label: 'Running scheduler' },
  { key: 'urgent', label: 'Creating urgent pickup' },
  { key: 'agentAction', label: 'Simulating agent action' },
];

const STEP_DELAY = 3000;

export function DemoButton() {
  const [demoState, setDemoState] = useState('idle');
  const [currentStep, setCurrentStep] = useState(-1);
  const [statusMessage, setStatusMessage] = useState('');
  const pauseRef = useRef(false);
  const stopRef = useRef(false);
  const timeoutsRef = useRef([]);

  const clearAllTimeouts = () => {
    timeoutsRef.current.forEach(clearTimeout);
    timeoutsRef.current = [];
  };

  const waitWhilePaused = () =>
    new Promise((resolve) => {
      const check = () => {
        if (stopRef.current) return resolve(false);
        if (!pauseRef.current) return resolve(true);
        setTimeout(check, 200);
      };
      check();
    });

  const runStep = async (stepKey) => {
    switch (stepKey) {
      case 'seed': {
        const loginResult = await api.login({ username: 'agent1', password: 'courier123' });
        if (loginResult.access_token) {
          localStorage.setItem('agent_token', loginResult.access_token);
        }
        await api.seedDemo(true);
        setStatusMessage('Seeded 3 agents and 6 pickups');
        break;
      }
      case 'schedule': {
        const result = await api.runScheduler();
        setStatusMessage(`Scheduled ${result.scheduled}, unassigned ${result.unassigned}`);
        break;
      }
      case 'urgent': {
        const result = await api.createUrgent();
        setStatusMessage(`Urgent pickup created: ${result.request?.id?.slice(0, 8) || 'N/A'}`);
        break;
      }
      case 'agentAction': {
        const requests = await api.getRequests({ status: 'Scheduled' });
        if (requests.length > 0) {
          const me = await api.getMe().catch(() => null);
          const target = (me && requests.find((r) => r.assigned_agent_id === me.id)) || requests[0];
          await api.updateStatus(target.id, 'En route');
          setStatusMessage(`Agent marked pickup ${target.id.slice(0, 8)} as En route`);
        } else {
          setStatusMessage('No scheduled requests to update');
        }
        break;
      }
      default:
        break;
    }
  };

  const startDemo = useCallback(async () => {
    pauseRef.current = false;
    stopRef.current = false;
    setDemoState('running');
    setCurrentStep(0);

    for (let i = 0; i < DEMO_STEPS.length; i++) {
      if (stopRef.current) break;
      setCurrentStep(i);
      setStatusMessage(DEMO_STEPS[i].label + '...');

      try {
        const stepPromise = runStep(DEMO_STEPS[i].key);
        const delayPromise = new Promise((resolve) =>
          timeoutsRef.current.push(setTimeout(resolve, STEP_DELAY))
        );

        await Promise.all([stepPromise, delayPromise]);
      } catch (err) {
        setStatusMessage(`Error: ${err.message || 'Demo step failed'}`);
        setDemoState('idle');
        return;
      }

      const resumed = await waitWhilePaused();
      if (!resumed) break;
    }

    if (!stopRef.current) {
      setDemoState('completed');
      setStatusMessage('Demo completed');
    } else {
      setDemoState('idle');
      setStatusMessage('');
      setCurrentStep(-1);
    }
  }, []);


  const togglePause = () => {
    pauseRef.current = !pauseRef.current;
    setDemoState(pauseRef.current ? 'paused' : 'running');
  };

  const stopDemo = () => {
    stopRef.current = true;
    pauseRef.current = false;
    clearAllTimeouts();
    setDemoState('idle');
    setStatusMessage('');
    setCurrentStep(-1);
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-gray-900">Live Demo</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Watch the scheduling system work end-to-end
          </p>
        </div>
        <div className="flex items-center gap-2">
          {demoState === 'idle' && (
            <button
              onClick={startDemo}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-md text-xs font-medium shadow-sm transition-colors"
            >
              Run Demo
            </button>
          )}
          {(demoState === 'running' || demoState === 'paused') && (
            <>
              <button
                onClick={togglePause}
                className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-md text-xs font-medium border border-gray-300 transition-colors"
              >
                {demoState === 'paused' ? 'Resume' : 'Pause'}
              </button>
              <button
                onClick={stopDemo}
                className="px-3 py-1.5 bg-red-50 hover:bg-red-100 text-red-700 rounded-md text-xs font-medium border border-red-200 transition-colors"
              >
                Stop
              </button>
            </>
          )}
          {demoState === 'completed' && (
            <button
              onClick={startDemo}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-md text-xs font-medium shadow-sm transition-colors"
            >
              Run Again
            </button>
          )}
        </div>
      </div>

      {demoState !== 'idle' && (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <div className="flex-1">
              <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                <span>Step {Math.min(currentStep + 1, DEMO_STEPS.length)} of {DEMO_STEPS.length}</span>
                <span>{statusMessage}</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-2">
                <div
                  className="bg-indigo-600 h-2 rounded-full transition-all duration-500"
                  style={{
                    width: `${((currentStep + 1) / DEMO_STEPS.length) * 100}%`,
                  }}
                />
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {DEMO_STEPS.map((step, idx) => (
              <div
                key={step.key}
                className={`flex items-center gap-1.5 text-xs ${
                  idx < currentStep
                    ? 'text-green-600'
                    : idx === currentStep
                    ? 'text-indigo-600'
                    : 'text-gray-400'
                }`}
              >
                <span
                  className={`w-4 h-4 rounded-full flex items-center justify-center text-xs ${
                    idx < currentStep
                      ? 'bg-green-100'
                      : idx === currentStep
                      ? 'bg-indigo-100'
                      : 'bg-gray-100'
                  }`}
                >
                  {idx < currentStep ? '✓' : idx + 1}
                </span>
                <span className="hidden sm:inline">{step.label.split(' ')[1]}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default DemoButton;
