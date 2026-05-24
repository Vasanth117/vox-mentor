import { useState, useRef, useEffect } from 'react';
import { getPresets, runCode, visualize } from '../api';
import * as d3 from 'd3';
import { 
  Play, Pause, SkipForward, SkipBack, ChevronFirst, ChevronLast, 
  Loader, BarChart3, Share2, Repeat, List, ArrowLeft, 
  Timer, Database, Cpu, Sparkles, Activity
} from 'lucide-react';

const SORT_COLORS = {
  active:    '#00d4ff',
  comparing: '#f97316',
  sorted:    '#10d98e',
  default:   '#8b5cf6',
};

const CATEGORY_ICONS = {
  'Sorting': <BarChart3 size={24} />,
  'Graphs': <Share2 size={24} />,
  'Recursion': <Repeat size={24} />,
  'Data Structures': <Database size={24} />,
};

const ALGO_ICONS = {
  'sorting': <BarChart3 size={18} />,
  'graph':   <Share2 size={18} />,
  'recursion': <Repeat size={18} />,
  'list': <List size={18} />,
  'array': <List size={18} />,
  'linked_list': <List size={18} />,
  'stack': <Database size={18} />,
  'queue': <Database size={18} />,
};

function getInputPlaceholder(selected) {
  if (!selected) return '';
  if (selected.id === 'binary_search') return 'Example: 1,3,5,7,9';
  if (selected.id === 'bfs' || selected.id === 'dfs') {
    return 'Optional JSON: {"nodes":["A","B","C"],"edges":[["A","B"],["B","C"]],"start":"A"}';
  }
  if (selected.id === 'factorial_recursion' || selected.id === 'fibonacci_recursion') return 'Example: 6';
  if (selected.id === 'stack_push_pop') return 'Example: push 5,push 10,pop';
  if (selected.id === 'queue_enqueue') return 'Example: enqueue 5,enqueue 10,dequeue';
  return 'Example: 5,1,4,2,8';
}

function toPythonList(values) {
  return `[${values.map((value) => Number(value)).join(', ')}]`;
}

function parseNumbers(raw, fallback = [5, 1, 4, 2, 8]) {
  const text = (raw || '').trim();
  if (!text) return fallback;
  const main = text.includes('|') ? text.split('|')[0] : text;
  const nums = main.split(',').map((item) => Number(item.trim())).filter((n) => Number.isFinite(n));
  return nums.length ? nums : fallback;
}

function buildLiveCode(selected, customInput, customTarget = '') {
  if (!selected) return '# Select an algorithm to preview code\n';
  const values = parseNumbers(customInput, [5, 1, 4, 2, 8]);
  const arrLiteral = toPythonList(values);

  if (selected.id === 'factorial_recursion') {
    const n = Number((customInput || '').trim()) || 5;
    return `def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)\n\nprint(factorial(${Math.max(0, Math.floor(n))}))\n`;
  }

  if (selected.id === 'fibonacci_recursion') {
    const n = Number((customInput || '').trim()) || 6;
    return `def fib(n):\n    if n <= 1:\n        return n\n    return fib(n - 1) + fib(n - 2)\n\nprint(fib(${Math.max(0, Math.floor(n))}))\n`;
  }

  if (selected.id === 'binary_search') {
    const parsedTarget = Number((customTarget || '').trim());
    const target = Number.isFinite(parsedTarget)
      ? parsedTarget
      : (values[Math.floor(values.length / 2)] || 0);
    return `arr = sorted(${arrLiteral})\ntarget = ${target}\n\nleft, right = 0, len(arr) - 1\nfound = -1\nwhile left <= right:\n    mid = (left + right) // 2\n    if arr[mid] == target:\n        found = mid\n        break\n    if arr[mid] < target:\n        left = mid + 1\n    else:\n        right = mid - 1\n\nprint(f"array={arr}")\nprint(f"target={target}, index={found}")\n`;
  }

  if (selected.id === 'stack_push_pop') {
    const operations = (customInput || 'push 5,push 10,pop').split(',').map((s) => s.trim()).filter(Boolean);
    const opsLiteral = JSON.stringify(operations);
    return `ops = ${opsLiteral}\nstack = []\nfor op in ops:\n    parts = op.split()\n    cmd = parts[0].lower()\n    if cmd == 'push' and len(parts) > 1:\n        stack.append(int(parts[1]))\n    elif cmd == 'pop' and stack:\n        stack.pop()\nprint(stack)\n`;
  }

  if (selected.id === 'queue_enqueue') {
    const operations = (customInput || 'enqueue 5,enqueue 10,dequeue').split(',').map((s) => s.trim()).filter(Boolean);
    const opsLiteral = JSON.stringify(operations);
    return `ops = ${opsLiteral}\nqueue = []\nfor op in ops:\n    parts = op.split()\n    cmd = parts[0].lower()\n    if cmd == 'enqueue' and len(parts) > 1:\n        queue.append(int(parts[1]))\n    elif cmd == 'dequeue' and queue:\n        queue.pop(0)\nprint(queue)\n`;
  }

  if (selected.id === 'linked_list') {
    return `values = ${arrLiteral}\nlinked = []\nfor value in values:\n    linked.append(value)\nprint(" -> ".join(map(str, linked)) if linked else "(empty)")\n`;
  }

  return `arr = ${arrLiteral}\n\nfor i in range(len(arr)):\n    for j in range(0, len(arr) - i - 1):\n        if arr[j] > arr[j + 1]:\n            arr[j], arr[j + 1] = arr[j + 1], arr[j]\n\nprint(arr)\n`;
}

function SortingViz({ steps, currentStep, speed }) {
  const svgRef = useRef(null);

  useEffect(() => {
    if (!steps?.length || currentStep >= steps.length) return;
    const step = steps[currentStep];
    const arr = step?.state?.array;
    if (!Array.isArray(arr)) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const W = svgRef.current.clientWidth || 560;
    const H = 220;
    const maxVal = Math.max(...arr);
    const barW = Math.max(8, (W - 40) / arr.length - 2);
    const scale = (H - 40) / maxVal;

    svg.attr('width', W).attr('height', H);

    const highlights = new Set(step.highlight_indices || []);
    const comparing = step.comparison || {};

    arr.forEach((val, i) => {
      const bh = val * scale;
      const x = 20 + i * ((W - 40) / arr.length);
      let fill = SORT_COLORS.default;
      if (highlights.has(i)) fill = SORT_COLORS.active;
      if (i === comparing.left || i === comparing.right) fill = SORT_COLORS.comparing;
      if (step.swap && highlights.has(i)) fill = SORT_COLORS.sorted;

      const g = svg.append('g');
      
      g.append('rect')
        .attr('x', x).attr('y', H - bh - 20)
        .attr('width', barW).attr('height', bh)
        .attr('rx', 4)
        .attr('fill', fill)
        .attr('opacity', 0)
        .transition().duration(speed * 0.4)
        .attr('opacity', 1);

      if (arr.length <= 20) {
        g.append('text')
          .attr('x', x + barW / 2).attr('y', H - 6)
          .attr('text-anchor', 'middle')
          .attr('fill', '#9CA3AF')
          .attr('font-size', 10)
          .attr('font-weight', 600)
          .text(val);
      }
    });
  }, [steps, currentStep, speed]);

  return <svg ref={svgRef} style={{ width:'100%', height:240 }} />;
}

function RecursionViz({ steps, currentStep }) {
  const step = steps?.[currentStep];
  const stack = step?.state?.call_stack || [];
  return (
    <div style={{ padding:16, display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ fontSize:'0.75rem', color:'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Execution Call Stack</div>
      {[...stack].reverse().map((frame, i) => (
        <div key={i} className="" style={{
          padding:'12px 18px', 
          background: i===0 ? 'rgba(59, 201, 219, 0.1)' : 'rgba(255,255,255,0.02)',
          border: `1px solid ${i===0 ? 'var(--accent-cyan)' : 'var(--border-glass)'}`,
          borderRadius: 12, 
          fontFamily:'var(--font-code)',
          fontSize:'0.85rem', 
          color: i===0 ? 'var(--accent-cyan)' : 'var(--text-secondary)',
          transform: `translateX(${i * 6}px)`,
          transition: 'all 0.3s ease',
          boxShadow: i===0 ? '0 0 15px rgba(59, 201, 219, 0.2)' : 'none'
        }}>
          {typeof frame === 'object' ? JSON.stringify(frame) : frame}
        </div>
      ))}
      {stack.length === 0 && <div style={{ color:'var(--text-muted)', textAlign: 'center', padding: 20 }}>Stack is currently empty</div>}
    </div>
  );
}

function GraphViz({ steps, currentStep }) {
  const step = steps?.[currentStep];
  const visited = new Set(step?.state?.visited || []);
  const current = step?.state?.current;
  const queue   = step?.state?.queue || step?.state?.stack || [];

  const nodes = step?.state?.nodes || [];
  const edges = step?.state?.edges || [];

  if (!nodes.length) {
    return (
      <div style={{ padding:30, textAlign:'center' }}>
        <div style={{ marginBottom:16 }}>
          {queue.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center' }}>
              <span style={{ color:'var(--text-muted)', fontSize:'0.8rem', width: '100%', marginBottom: 4 }}>Processing Lineage: </span>
              {queue.map((n, i) => (
                <span key={i} style={{
                  padding:'6px 12px', borderRadius: 10,
                  background:'rgba(59, 201, 219, 0.1)', border:'1px solid var(--accent-cyan)',
                  color:'var(--accent-cyan)', fontSize:'0.8rem', fontWeight: 600
                }}>{n}</span>
              ))}
            </div>
          )}
        </div>
        <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{step?.action}</span>
      </div>
    );
  }

  return (
    <svg style={{ width:'100%', height:240 }}>
      {edges.map((e, i) => (
        <line key={i} x1={e.x1} y1={e.y1} x2={e.x2} y2={e.y2}
          stroke="var(--border-glass)" strokeWidth={2} />
      ))}
      {nodes.map((n, i) => {
        const isVisited = visited.has(n.id);
        const isCurrent = n.id === current;
        return (
          <g key={i}>
            <circle cx={n.x} cy={n.y} r={26}
              fill={isCurrent ? 'var(--accent-cyan)' : isVisited ? 'rgba(16,217,142,0.15)' : 'rgba(11, 15, 25, 0.8)'}
              stroke={isCurrent ? 'var(--accent-cyan)' : isVisited ? 'var(--accent-green)' : 'var(--border-glass)'}
              strokeWidth={3}
              style={{ transition: 'all 0.4s ease' }} />
            <text x={n.x} y={n.y+6} textAnchor="middle"
              fill={isCurrent ? '#fff' : 'var(--text-primary)'} fontSize={14} fontWeight={700}>{n.id}</text>
          </g>
        );
      })}
    </svg>
  );
}

function ArrayViz({ steps, currentStep }) {
  const step = steps?.[currentStep];
  const state = step?.state || {};
  const array = Array.isArray(state.array) ? state.array : [];
  const highlights = new Set(step?.highlight_indices || []);
  const left = Number.isInteger(state.left) ? state.left : null;
  const right = Number.isInteger(state.right) ? state.right : null;
  const target = state.target;

  if (!array.length) {
    return <div style={{ color:'var(--text-muted)', textAlign:'center', padding: 24 }}>No data to render for this step.</div>;
  }

  return (
    <div style={{ width: '100%', display:'flex', flexDirection:'column', gap:12, padding: 12 }}>
      <div style={{ color: 'var(--text-muted)', fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 700 }}>
        {typeof target === 'number' ? `Target: ${target}` : 'Array state'}
      </div>
      <div style={{ display:'flex', flexWrap:'wrap', gap:10 }}>
        {array.map((item, index) => {
          let border = '1px solid rgba(59, 201, 219, 0.4)';
          let bg = 'rgba(59, 201, 219, 0.12)';
          let color = 'var(--accent-cyan)';
          if (index === left || index === right) {
            border = '1px solid rgba(249, 115, 22, 0.8)';
            bg = 'rgba(249, 115, 22, 0.15)';
            color = '#fb923c';
          }
          if (highlights.has(index)) {
            border = '1px solid rgba(16, 217, 142, 0.9)';
            bg = 'rgba(16, 217, 142, 0.15)';
            color = 'var(--accent-green)';
          }
          return (
            <div key={`${item}-${index}`} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>[{index}]</div>
              <div style={{
                minWidth: 48,
                padding:'10px 14px',
                borderRadius: 10,
                background: bg,
                border,
                color,
                fontFamily:'var(--font-code)',
                fontWeight: 700,
                textAlign:'center'
              }}>
                {String(item)}
              </div>
            </div>
          );
        })}
      </div>
      <div style={{ display: 'flex', gap: 16, fontSize: '0.72rem', color: 'var(--text-muted)' }}>
        <span>L/R bounds: orange</span>
        <span>Current check: green</span>
      </div>
    </div>
  );
}

function LinkedListViz({ steps, currentStep }) {
  const step = steps?.[currentStep];
  const values = step?.state?.array || [];
  if (!values.length) {
    return <div style={{ color:'var(--text-muted)', textAlign:'center', padding: 24 }}>No linked-list nodes yet.</div>;
  }
  return (
    <div style={{ width:'100%', padding: 12, display:'flex', flexWrap:'wrap', alignItems:'center', gap: 8 }}>
      {values.map((item, index) => (
        <div key={`${item}-${index}`} style={{ display:'flex', alignItems:'center', gap:8 }}>
          <div style={{
            minWidth: 54,
            padding:'10px 14px',
            borderRadius: 10,
            background:'rgba(124, 92, 255, 0.15)',
            border:'1px solid rgba(124, 92, 255, 0.55)',
            color:'var(--accent-violet)',
            fontFamily:'var(--font-code)',
            fontWeight: 700,
            textAlign:'center'
          }}>
            {item}
          </div>
          {index < values.length - 1 && <span style={{ color:'var(--text-muted)', fontWeight: 800 }}>→</span>}
        </div>
      ))}
      <span style={{ color:'var(--text-muted)', marginLeft: 2 }}>∅</span>
    </div>
  );
}

function StackQueueViz({ steps, currentStep, type }) {
  const step = steps?.[currentStep];
  const state = step?.state || {};
  const listToRender = type === 'stack' ? (state.stack || []) : (state.queue || []);

  if (!listToRender.length) {
    return <div style={{ color:'var(--text-muted)', textAlign:'center', padding: 24 }}>No data to render for this step.</div>;
  }

  const renderList = type === 'stack' ? [...listToRender].reverse() : listToRender;

  return (
    <div style={{ width: '100%', display:'flex', flexDirection:'column', gap:12, padding: 12 }}>
      <div style={{ color: 'var(--text-muted)', fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 700 }}>
        {type === 'stack' ? 'Stack (top first)' : 'Queue (front first)'}
      </div>
      <div style={{ display:'flex', flexDirection: type === 'stack' ? 'column' : 'row', flexWrap:'wrap', gap:10, alignItems: type === 'stack' ? 'flex-start' : 'center' }}>
        {renderList.map((item, index) => (
          <div key={`${item}-${index}`} style={{ display:'flex', alignItems:'center', gap:8 }}>
            <div style={{
              minWidth: 52,
              padding:'10px 14px',
              borderRadius: 10,
              background:'rgba(59, 201, 219, 0.12)',
              border:'1px solid rgba(59, 201, 219, 0.45)',
              color:'var(--accent-cyan)',
              fontFamily:'var(--font-code)',
              fontWeight: 700,
              textAlign:'center'
            }}>
              {String(item)}
            </div>
            {type === 'queue' && index < renderList.length - 1 && <span style={{ color:'var(--text-muted)' }}>→</span>}
          </div>
        ))}
      </div>
    </div>
  );
}

function StructureViz({ steps, currentStep }) {
  const step = steps?.[currentStep];
  const state = step?.state || {};
  const array = state.array || [];
  if (!array.length) {
    return <div style={{ color:'var(--text-muted)', textAlign:'center', padding: 24 }}>No data to render for this step.</div>;
  }
  return (
    <div style={{ width:'100%', display:'flex', flexWrap:'wrap', gap:10, padding:12 }}>
      {array.map((item, index) => (
        <div key={`${item}-${index}`} style={{
          minWidth: 48,
          padding:'10px 14px',
          borderRadius: 10,
          background:'rgba(59, 201, 219, 0.12)',
          border:'1px solid rgba(59, 201, 219, 0.4)',
          color:'var(--accent-cyan)',
          fontFamily:'var(--font-code)',
          fontWeight: 700,
          textAlign:'center'
        }}>
          {String(item)}
        </div>
      ))}
    </div>
  );
}

export default function Visualizer() {
  const [presets, setPresets] = useState({ by_category: {} });
  const [selected, setSelected] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(600);
  const [customInput, setCustomInput] = useState('');
  const [customTarget, setCustomTarget] = useState('');
  const [liveCode, setLiveCode] = useState('');
  const [liveOutput, setLiveOutput] = useState('// Live output will appear here');
  const [runningCode, setRunningCode] = useState(false);
  const timerRef = useRef(null);

  const runLiveCode = async (codeText, lang = 'python') => {
    if (!codeText.trim()) {
      setLiveOutput('// No code to run');
      return;
    }
    setRunningCode(true);
    try {
      const { data: result } = await runCode(codeText, lang, '');
      const text = (result?.stdout || result?.stderr || '// (no output)').trim();
      setLiveOutput(text || '// (no output)');
    } catch {
      setLiveOutput('// Live run failed. Check backend status.');
    }
    setRunningCode(false);
  };

  useEffect(() => {
    getPresets().then(r => setPresets(r.data)).catch(() => {});
  }, []);

  const loadViz = async (preset) => {
    setSelected(preset);
    setLoading(true);
    setData(null);
    setCurrentStep(0);
    setPlaying(false);
    try {
      const { data: vdata } = await visualize(preset.id, 'python', customInput, customTarget);
      setData(vdata);
    } catch { setData(null); }
    setLoading(false);
  };

  const steps = data?.steps || [];
  const maxStep = steps.length - 1;

  const step = (n) => setCurrentStep(c => Math.max(0, Math.min(maxStep, c + n)));

  useEffect(() => {
    if (playing) {
      timerRef.current = setInterval(() => {
        setCurrentStep(c => {
          if (c >= maxStep) { setPlaying(false); clearInterval(timerRef.current); return c; }
          return c + 1;
        });
      }, speed);
    } else clearInterval(timerRef.current);
    return () => clearInterval(timerRef.current);
  }, [playing, speed, maxStep]);

  useEffect(() => {
    if (!selected) return;
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const { data: vdata } = await visualize(selected.id, 'python', customInput, customTarget);
        setData(vdata);
        setCurrentStep(0);
        setPlaying(false);
      } catch {
        setData(null);
      }
      setLoading(false);

      const codeText = buildLiveCode(selected, customInput, customTarget);
      setLiveCode(codeText);
      await runLiveCode(codeText, 'python');
    }, 450);

    return () => clearTimeout(timer);
  }, [selected, customInput, customTarget]);

  const VizComponent = selected?.type === 'recursion' ? RecursionViz
    : selected?.type === 'graph' ? GraphViz
    : selected?.type === 'sorting' ? SortingViz
    : selected?.type === 'array' ? ArrayViz
    : selected?.type === 'linked_list' ? LinkedListViz
    : selected?.type === 'stack' ? ((props) => <StackQueueViz {...props} type="stack" />)
    : selected?.type === 'queue' ? ((props) => <StackQueueViz {...props} type="queue" />)
    : StructureViz;

  if (!selected) {
    return (
      <div className="fade-in" style={{ paddingBottom: 60 }}>
        <div className="page-header" style={{ textAlign: 'center', marginBottom: 60 }}>
          <h1 className="page-title" style={{ fontSize: '2.5rem', letterSpacing: '-0.02em' }}>Algorithm Intelligence</h1>
          <p className="page-subtitle">Understand logic through high-fidelity visual simulations</p>
        </div>

        <div style={{ maxWidth: 1000, margin: '0 auto' }}>
          {Object.entries(presets.by_category || {}).map(([cat, items]) => (
            <div key={cat} style={{ marginBottom: 48 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24, paddingLeft: 8 }}>
                <div style={{ padding: 10, background: 'rgba(59, 201, 219, 0.1)', borderRadius: 12, color: 'var(--accent-cyan)' }}>
                  {CATEGORY_ICONS[cat] || <Activity size={24} />}
                </div>
                <h3 style={{ fontSize:'1.25rem', fontWeight:800, color:'var(--text-primary)', letterSpacing: '-0.01em' }}>{cat}</h3>
              </div>
              
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', 
                gap: 20 
              }}>
                {items.map(preset => (
                  <button key={preset.id} onClick={() => loadViz(preset)}
                    className="glass"
                    style={{
                      display:'flex', flexDirection: 'column', gap:16, padding: 24,
                      background: 'var(--bg-glass)',
                      border: '1px solid var(--border-glass)',
                      borderRadius: 24, cursor:'pointer', color:'var(--text-primary)',
                      textAlign:'left', transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                      position: 'relative', overflow: 'hidden'
                    }}
                    onMouseEnter={e => { 
                      e.currentTarget.style.transform = 'translateY(-6px)';
                      e.currentTarget.style.borderColor = 'var(--accent-cyan)';
                      e.currentTarget.style.boxShadow = '0 12px 30px rgba(0,0,0,0.4), 0 0 20px rgba(59, 201, 219, 0.1)';
                    }}
                    onMouseLeave={e => { 
                      e.currentTarget.style.transform = 'translateY(0)';
                      e.currentTarget.style.borderColor = 'var(--border-glass)';
                      e.currentTarget.style.boxShadow = 'none';
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ color: 'var(--accent-cyan)' }}>
                         {ALGO_ICONS[preset.type] || <Cpu size={18} />}
                      </div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                        Simulation
                      </div>
                    </div>
                    <div>
                      <h4 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: 6 }}>{preset.label}</h4>
                      <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                        Step-by-step interactive breakdown of the {preset.label} process.
                      </p>
                    </div>
                    <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                       <span style={{ fontSize: '0.65rem', padding: '4px 10px', borderRadius: 10, background: 'rgba(255,255,255,0.05)', color: 'var(--text-muted)', fontWeight: 600 }}>AUTO</span>
                       <span style={{ fontSize: '0.65rem', padding: '4px 10px', borderRadius: 10, background: 'rgba(255,255,255,0.05)', color: 'var(--text-muted)', fontWeight: 600 }}>60FPS</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in" style={{ maxWidth: 1000, margin: '0 auto', paddingBottom: 60 }}>
      <button 
        onClick={() => setSelected(null)} 
        className="btn-ghost" 
        style={{ marginBottom: 24, display: 'flex', alignItems: 'center', gap: 8, padding: '10px 16px', borderRadius: 12 }}
      >
        <ArrowLeft size={18} /> Back to Library
      </button>

      <div className="card" style={{ padding:0, overflow:'hidden', borderRadius: 32, border: '1px solid var(--border-glass)', background: 'var(--bg-glass)', boxShadow: '0 30px 60px rgba(0,0,0,0.4)' }}>
        {/* Title bar */}
        <div style={{ padding:'24px 32px', borderBottom:'1px solid var(--border-glass)', background:'rgba(255,255,255,0.02)' }}>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                <div style={{ color: 'var(--accent-cyan)' }}>
                  {ALGO_ICONS[selected.type] || <Cpu size={18} />}
                </div>
                <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  {selected.type} Visualizer
                </span>
              </div>
              <h2 style={{ fontSize: '1.8rem', fontWeight: 800, margin: 0 }}>{selected.label}</h2>
            </div>
            <div style={{ display:'flex', gap:10 }}>
              {data?.time_complexity && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 12, background: 'rgba(59, 201, 219, 0.1)', border: '1px solid rgba(59, 201, 219, 0.2)' }}>
                   <Timer size={14} color="var(--accent-cyan)" />
                   <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>{data.time_complexity}</span>
                </div>
              )}
              {data?.space_complexity && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 12, background: 'rgba(124, 92, 255, 0.1)', border: '1px solid rgba(124, 92, 255, 0.2)' }}>
                   <Database size={14} color="var(--accent-violet)" />
                   <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-violet)' }}>{data.space_complexity}</span>
                </div>
              )}
            </div>
          </div>
        </div>

        <div style={{ padding:'16px 32px', borderBottom:'1px solid var(--border-glass)', background:'rgba(255,255,255,0.015)' }}>
          <div style={{ display:'flex', gap:10, alignItems:'center', flexWrap:'wrap' }}>
            <input
              className="input"
              value={customInput}
              onChange={(e) => setCustomInput(e.target.value)}
              placeholder={getInputPlaceholder(selected)}
              style={{ flex:1, minWidth: 280 }}
            />
            {selected?.id === 'binary_search' && (
              <input
                className="input"
                value={customTarget}
                onChange={(e) => setCustomTarget(e.target.value)}
                placeholder="Target (e.g. 7)"
                style={{ width: 180 }}
              />
            )}
            <button className="btn btn-secondary" onClick={() => {
              const codeText = buildLiveCode(selected, customInput, customTarget);
              setLiveCode(codeText);
              runLiveCode(codeText, 'python');
            }} disabled={runningCode}>
              {runningCode ? <Loader size={16} className="spin" /> : <Play size={16} />} Run Live Code
            </button>
          </div>
        </div>

        {/* Viz area */}
        <div style={{ padding: 24, minHeight: 420, background:'#05070a' }}>
          <div style={{ display:'grid', gridTemplateColumns:'1.15fr 0.85fr', gap:16, alignItems:'stretch' }}>
            <div style={{ border:'1px solid var(--border-glass)', borderRadius:16, padding:16, display:'flex', alignItems:'center', justifyContent:'center', background:'rgba(255,255,255,0.01)' }}>
              {loading ? (
                <div style={{ display:'flex', flexDirection: 'column', alignItems:'center', justifyContent:'center', gap:20 }}>
                  <div className="spinner" style={{ width: 44, height: 44, borderTopColor: 'var(--accent-cyan)' }} />
                  <span style={{ color:'var(--text-muted)', fontWeight: 600, fontSize: '0.9rem' }}>Compiling visual state...</span>
                </div>
              ) : data ? (
                <div style={{ width: '100%' }}>
                  <VizComponent steps={steps} currentStep={currentStep} speed={speed} />
                </div>
              ) : (
                <div style={{ display:'flex', flexDirection: 'column', alignItems:'center', gap: 16 }}>
                  <Sparkles size={40} color="var(--text-muted)" />
                  <span style={{ color:'var(--text-muted)', fontWeight: 500 }}>Engine response pending. Verify AI server status.</span>
                </div>
              )}
            </div>

            <div style={{ border:'1px solid var(--border-glass)', borderRadius:16, overflow:'hidden', display:'flex', flexDirection:'column', minHeight: 320, background:'rgba(255,255,255,0.015)' }}>
              <div style={{ padding:'10px 12px', borderBottom:'1px solid var(--border-glass)', color:'var(--text-muted)', fontSize:'0.75rem', fontWeight:700, textTransform:'uppercase', letterSpacing:'0.05em' }}>
                Live Python Code
              </div>
              <pre style={{ margin:0, padding:'12px', flex:1, overflow:'auto', fontSize:'0.78rem', lineHeight:1.5, fontFamily:'var(--font-code)', color:'#e6edf3', background:'#0d1117' }}>
                {liveCode || buildLiveCode(selected, customInput, customTarget)}
              </pre>
              <div style={{ padding:'10px 12px', borderTop:'1px solid var(--border-glass)', color:'var(--text-muted)', fontSize:'0.75rem', fontWeight:700, textTransform:'uppercase', letterSpacing:'0.05em' }}>
                Live Output
              </div>
              <pre style={{ margin:0, padding:'12px', minHeight:90, maxHeight:140, overflow:'auto', fontSize:'0.78rem', lineHeight:1.5, fontFamily:'var(--font-code)', color:'var(--text-secondary)', background:'#0a0f17' }}>
                {runningCode ? 'Running…' : liveOutput}
              </pre>
            </div>
          </div>
        </div>

        {/* Step info */}
        {data && steps[currentStep] && (
          <div style={{ padding:'20px 32px', background:'rgba(255,255,255,0.02)', borderTop:'1px solid var(--border-glass)', display: 'flex', gap: 16 }}>
             <div style={{ padding: '4px 12px', borderRadius: 8, background: 'var(--accent-cyan)', color: '#000', fontWeight: 800, fontSize: '0.7rem', height: 'fit-content' }}>
                STEP {currentStep + 1}
             </div>
             <p style={{ margin: 0, fontSize: '0.95rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
               {steps[currentStep].action}
             </p>
          </div>
        )}

        {/* Controls */}
        {data && (
          <div className="viz-controls" style={{ padding: '24px 32px', background: 'var(--bg-primary)', borderTop:'1px solid var(--border-glass)', borderRadius:0 }}>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-ghost btn-icon" onClick={() => setCurrentStep(0)} style={{ width: 44, height: 44 }}><ChevronFirst size={20} /></button>
              <button className="btn btn-ghost btn-icon" onClick={() => step(-1)} style={{ width: 44, height: 44 }}><SkipBack size={20} /></button>
              <button className={`btn ${playing?'btn-secondary':'btn-primary'} btn-icon`}
                onClick={() => setPlaying(p => !p)} style={{ width: 56, height: 56, borderRadius: 16 }}>
                {playing ? <Pause size={24} /> : <Play size={24} />}
              </button>
              <button className="btn btn-ghost btn-icon" onClick={() => step(1)} style={{ width: 44, height: 44 }}><SkipForward size={20} /></button>
              <button className="btn btn-ghost btn-icon" onClick={() => setCurrentStep(maxStep)} style={{ width: 44, height: 44 }}><ChevronLast size={20} /></button>
            </div>

            <div style={{ display:'flex', alignItems:'center', gap:20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ fontSize:'0.75rem', fontWeight: 700, color:'var(--text-muted)', textTransform: 'uppercase' }}>Simulation Speed</span>
                <input type="range" min={100} max={1500} step={100} value={speed}
                  onChange={e => setSpeed(Number(e.target.value))}
                  style={{ width:120, accentColor:'var(--accent-cyan)' }} />
              </div>

              {/* Progress */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, width: 150 }}>
                <div className="progress-bar" style={{ flex:1, height: 6 }}>
                  <div className="progress-fill" style={{ width: steps.length > 1 ? `${(currentStep / (steps.length-1)) * 100}%` : '0%' }} />
                </div>
                <span style={{ fontSize:'0.75rem', fontWeight: 800, color:'var(--accent-cyan)', fontVariantNumeric: 'tabular-nums' }}>
                  {maxStep > 0 ? Math.round((currentStep / maxStep) * 100) : 0}%
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
