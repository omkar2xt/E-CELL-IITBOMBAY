// pages/WhatIfSimulator.jsx — StorePulse AI
// Interactive What-If Floor Plan Layout Editor
// Developer: Omkar Gurav
// Uses SVG + React state for drag-and-drop without external DnD libraries
import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Save, Trash2, RotateCcw, RotateCw, Copy, Info, Plus, Layout,
  Grid, Move, Maximize2, Undo, Play, AlertTriangle, CheckCircle2, ShieldAlert
} from 'lucide-react';

const API = 'http://localhost:8000';

const ELEMENT_TYPES = [
  { type: 'shelf',    label: 'Shelf',     color: '#6366f1', bg: 'rgba(99,102,241,0.15)',  icon: '🗄' },
  { type: 'checkout', label: 'Checkout',  color: '#10b981', bg: 'rgba(16,185,129,0.15)',  icon: '🛒' },
  { type: 'display',  label: 'Display',   color: '#8b5cf6', bg: 'rgba(139,92,246,0.15)',  icon: '📦' },
  { type: 'entrance', label: 'Entrance',  color: '#f59e0b', bg: 'rgba(245,158,11,0.15)',  icon: '🚪' },
  { type: 'exit',     label: 'Exit',      color: '#06b6d4', bg: 'rgba(6,182,212,0.15)',   icon: '🚪' },
  { type: 'obstacle', label: 'Obstacle',  color: '#ef4444', bg: 'rgba(239,68,68,0.15)',   icon: '🚧' },
];

const GRID_SIZE = 40;   // px — snap grid
const CANVAS_W = 800;
const CANVAS_H = 500;

function snapToGrid(v) { return Math.round(v / GRID_SIZE) * GRID_SIZE; }

function makeId() { return `el_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`; }

const DEFAULT_ELEMENTS = [
  { id: 's1', element_type: 'shelf',    x: 200, y: 40,  width: 80, height: 160, rotation: 0, label: 'Shelf A' },
  { id: 's2', element_type: 'shelf',    x: 320, y: 40,  width: 80, height: 160, rotation: 0, label: 'Shelf B' },
  { id: 's3', element_type: 'shelf',    x: 440, y: 40,  width: 80, height: 160, rotation: 0, label: 'Shelf C' },
  { id: 's4', element_type: 'shelf',    x: 560, y: 40,  width: 80, height: 160, rotation: 0, label: 'Shelf D' },
  { id: 's5', element_type: 'shelf',    x: 200, y: 280, width: 80, height: 160, rotation: 0, label: 'Shelf E' },
  { id: 's6', element_type: 'shelf',    x: 320, y: 280, width: 80, height: 160, rotation: 0, label: 'Shelf F' },
  { id: 's7', element_type: 'shelf',    x: 440, y: 280, width: 80, height: 160, rotation: 0, label: 'Shelf G' },
  { id: 'c1', element_type: 'checkout', x: 40,  y: 40,  width: 120, height: 160, rotation: 0, label: 'Checkout' },
  { id: 'e1', element_type: 'entrance', x: 0,   y: 380, width: 80,  height: 80, rotation: 0,  label: 'Entrance' },
  { id: 'd1', element_type: 'display',  x: 300, y: 120, width: 60,  height: 100, rotation: 0, label: 'Promo' },
];

export default function WhatIfSimulator() {
  const navigate = useNavigate();
  const [elements, setElements] = useState(DEFAULT_ELEMENTS);
  const [undoStack, setUndoStack] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [activeType, setActiveType] = useState('shelf');
  const [mode, setMode] = useState('select'); // 'select' | 'add'
  const [layoutName, setLayoutName] = useState('Proposed Layout 1');
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [savedMsg, setSavedMsg] = useState('');
  const [layouts, setLayouts] = useState([]);
  const [showLayouts, setShowLayouts] = useState(false);

  const svgRef = useRef(null);
  const dragging = useRef(null);   // { id, startX, startY, elX, elY, initialElements }
  const resizing = useRef(null);   // { id, startX, startY, w0, h0, initialElements }

  // Load layouts from backend on mount
  useEffect(() => {
    fetchLayouts();
  }, []);

  const fetchLayouts = async () => {
    try {
      const res = await fetch(`${API}/api/layouts/`);
      const json = await res.json();
      setLayouts(json.layouts || []);
    } catch { }
  };

  const pushHistory = (currentEls = elements) => {
    setUndoStack(prev => [...prev.slice(-19), JSON.parse(JSON.stringify(currentEls))]);
  };

  const undo = () => {
    if (undoStack.length === 0) return;
    const prev = undoStack[undoStack.length - 1];
    setUndoStack(s => s.slice(0, -1));
    setElements(prev);
    setValidationResult(null);
  };

  // ── Collision / Overlap detection ──────────────────────────────────
  const findOverlaps = () => {
    const pairs = [];
    const collidingIds = new Set();
    for (let i = 0; i < elements.length; i++) {
      for (let j = i + 1; j < elements.length; j++) {
        const a = elements[i];
        const b = elements[j];
        if (a.x < b.x + b.width && a.x + a.width > b.x &&
            a.y < b.y + b.height && a.y + a.height > b.y) {
          pairs.push({
            labelA: a.label || a.id,
            labelB: b.label || b.id,
            idA: a.id,
            idB: b.id,
          });
          collidingIds.add(a.id);
          collidingIds.add(b.id);
        }
      }
    }
    return { pairs, collidingIds };
  };

  const { pairs: overlapPairs, collidingIds } = findOverlaps();

  // ── Canvas event handlers ──────────────────────────────────────────

  const getSVGCoords = (e) => {
    const svg = svgRef.current;
    const rect = svg.getBoundingClientRect();
    const scaleX = CANVAS_W / rect.width;
    const scaleY = CANVAS_H / rect.height;
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY,
    };
  };

  const handleCanvasClick = (e) => {
    if (mode !== 'add') return;
    pushHistory();
    const { x, y } = getSVGCoords(e);
    const typeInfo = ELEMENT_TYPES.find(t => t.type === activeType);
    const newEl = {
      id: makeId(),
      element_type: activeType,
      x: snapToGrid(x - 40),
      y: snapToGrid(y - 40),
      width: activeType === 'entrance' || activeType === 'exit' ? 80 : activeType === 'checkout' ? 120 : 80,
      height: activeType === 'entrance' || activeType === 'exit' ? 80 : 160,
      rotation: 0,
      label: typeInfo?.label || activeType,
    };
    setElements(prev => [...prev, newEl]);
    setSelectedId(newEl.id);
    setMode('select');
    setValidationResult(null);
  };

  const handleElMouseDown = (e, id) => {
    e.stopPropagation();
    if (mode !== 'select') return;
    setSelectedId(id);
    const { x, y } = getSVGCoords(e);
    const el = elements.find(el => el.id === id);
    dragging.current = { id, startX: x, startY: y, elX: el.x, elY: el.y, snapshot: JSON.parse(JSON.stringify(elements)) };
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  };

  const handleResizeMouseDown = (e, id) => {
    e.stopPropagation();
    const { x, y } = getSVGCoords(e);
    const el = elements.find(el => el.id === id);
    resizing.current = { id, startX: x, startY: y, w0: el.width, h0: el.height, snapshot: JSON.parse(JSON.stringify(elements)) };
    window.addEventListener('mousemove', handleResizeMove);
    window.addEventListener('mouseup', handleResizeUp);
  };

  const handleMouseMove = useCallback((e) => {
    if (!dragging.current) return;
    const { x, y } = getSVGCoords(e);
    const dx = x - dragging.current.startX;
    const dy = y - dragging.current.startY;
    const nx = snapToGrid(dragging.current.elX + dx);
    const ny = snapToGrid(dragging.current.elY + dy);
    setElements(prev => prev.map(el =>
      el.id === dragging.current.id ? { ...el, x: Math.max(0, nx), y: Math.max(0, ny) } : el
    ));
    setValidationResult(null);
  }, []);

  const handleMouseUp = useCallback(() => {
    if (dragging.current && dragging.current.snapshot) {
      pushHistory(dragging.current.snapshot);
    }
    dragging.current = null;
    window.removeEventListener('mousemove', handleMouseMove);
    window.removeEventListener('mouseup', handleMouseUp);
  }, []);

  const handleResizeMove = useCallback((e) => {
    if (!resizing.current) return;
    const { x, y } = getSVGCoords(e);
    const dx = x - resizing.current.startX;
    const dy = y - resizing.current.startY;
    const nw = snapToGrid(Math.max(GRID_SIZE, resizing.current.w0 + dx));
    const nh = snapToGrid(Math.max(GRID_SIZE, resizing.current.h0 + dy));
    setElements(prev => prev.map(el =>
      el.id === resizing.current.id ? { ...el, width: nw, height: nh } : el
    ));
  }, []);

  const handleResizeUp = useCallback(() => {
    resizing.current = null;
    window.removeEventListener('mousemove', handleResizeMove);
    window.removeEventListener('mouseup', handleResizeUp);
  }, [handleResizeMove]);

  // ── Actions ────────────────────────────────────────────────────────

  const deleteSelected = () => {
    if (!selectedId) return;
    pushHistory();
    setElements(prev => prev.filter(e => e.id !== selectedId));
    setSelectedId(null);
    setValidationResult(null);
  };

  const duplicateSelected = () => {
    const el = elements.find(e => e.id === selectedId);
    if (!el) return;
    pushHistory();
    const newEl = { ...el, id: makeId(), x: Math.min(CANVAS_W - el.width, el.x + GRID_SIZE), y: Math.min(CANVAS_H - el.height, el.y + GRID_SIZE) };
    setElements(prev => [...prev, newEl]);
    setSelectedId(newEl.id);
    setValidationResult(null);
  };

  const rotateSelected = () => {
    const el = elements.find(e => e.id === selectedId);
    if (!el) return;
    pushHistory();
    setElements(prev => prev.map(e =>
      e.id === selectedId ? { ...e, rotation: ((e.rotation || 0) + 90) % 360 } : e
    ));
    setValidationResult(null);
  };

  const resetToDefault = () => {
    if (!window.confirm('Reset to default layout? All unsaved changes will be lost.')) return;
    pushHistory();
    setElements(DEFAULT_ELEMENTS);
    setSelectedId(null);
    setValidationResult(null);
  };

  const resetToBaseline = async () => {
    try {
      const res = await fetch(`${API}/api/layouts/baseline`);
      if (res.ok) {
        const json = await res.json();
        const layout = json.layout;
        if (layout?.elements) {
          pushHistory();
          const els = layout.elements.map(e => ({
            ...e,
            x: e.x <= 1.0 ? Math.round(e.x * CANVAS_W) : e.x,
            y: e.y <= 1.0 ? Math.round(e.y * CANVAS_H) : e.y,
            width: e.width <= 1.0 ? Math.round(e.width * CANVAS_W) : e.width,
            height: e.height <= 1.0 ? Math.round(e.height * CANVAS_H) : e.height,
          }));
          setElements(els);
          setLayoutName(`${layout.name || 'Baseline'} (Proposed)`);
          setSelectedId(null);
          setValidationResult(null);
          setSavedMsg('✓ Reset canvas to Baseline layout');
          setTimeout(() => setSavedMsg(''), 3000);
          return;
        }
      }
      resetToDefault();
    } catch {
      resetToDefault();
    }
  };

  const saveLayout = async (isBaseline = false) => {
    setSaving(true);
    try {
      const body = {
        name: isBaseline ? 'Baseline Layout' : layoutName,
        description: isBaseline ? 'Baseline layout saved from editor' : `Proposed layout: ${layoutName}`,
        elements: elements.map(e => ({
          ...e,
          x: e.x > 1 ? Number((e.x / CANVAS_W).toFixed(4)) : e.x,
          y: e.y > 1 ? Number((e.y / CANVAS_H).toFixed(4)) : e.y,
          width: e.width > 1 ? Number((e.width / CANVAS_W).toFixed(4)) : e.width,
          height: e.height > 1 ? Number((e.height / CANVAS_H).toFixed(4)) : e.height,
        })),
        zones: [],
        is_baseline: isBaseline,
        id: isBaseline ? 'baseline' : undefined,
      };
      const res = await fetch(`${API}/api/layouts/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        const saved = await res.json();
        setSavedMsg(isBaseline ? '✓ Saved as baseline' : '✓ Layout saved');
        fetchLayouts();
        setTimeout(() => setSavedMsg(''), 3000);
        return saved.id || (isBaseline ? 'baseline' : undefined);
      }
    } catch (e) {
      setSavedMsg('⚠ Save failed (backend offline)');
      setTimeout(() => setSavedMsg(''), 3000);
    } finally {
      setSaving(false);
    }
    return null;
  };

  const validateGeometry = async () => {
    setValidating(true);
    try {
      const body = {
        name: layoutName,
        description: 'Geometry validation request',
        elements: elements.map(e => ({
          ...e,
          x: e.x > 1 ? Number((e.x / CANVAS_W).toFixed(4)) : e.x,
          y: e.y > 1 ? Number((e.y / CANVAS_H).toFixed(4)) : e.y,
          width: e.width > 1 ? Number((e.width / CANVAS_W).toFixed(4)) : e.width,
          height: e.height > 1 ? Number((e.height / CANVAS_H).toFixed(4)) : e.height,
        })),
        zones: [],
      };
      const res = await fetch(`${API}/api/layouts/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        const json = await res.json();
        setValidationResult(json);
      }
    } catch {
      setSavedMsg('⚠ Backend offline for validation');
      setTimeout(() => setSavedMsg(''), 3000);
    } finally {
      setValidating(false);
    }
  };

  const simulateProposed = async () => {
    const savedId = await saveLayout(false);
    if (savedId) {
      navigate('/comparison');
    }
  };

  const loadLayout = async (id) => {
    try {
      const res = await fetch(`${API}/api/layouts/${id}`);
      const json = await res.json();
      const layout = json.layout;
      if (layout?.elements) {
        pushHistory();
        const els = layout.elements.map(e => ({
          ...e,
          x: e.x <= 1.0 ? Math.round(e.x * CANVAS_W) : e.x,
          y: e.y <= 1.0 ? Math.round(e.y * CANVAS_H) : e.y,
          width: e.width <= 1.0 ? Math.round(e.width * CANVAS_W) : e.width,
          height: e.height <= 1.0 ? Math.round(e.height * CANVAS_H) : e.height,
        }));
        setElements(els);
        setLayoutName(layout.name);
        setShowLayouts(false);
        setSelectedId(null);
        setValidationResult(null);
        setSavedMsg(`✓ Loaded: ${layout.name}`);
        setTimeout(() => setSavedMsg(''), 3000);
      }
    } catch { }
  };

  const selectedEl = elements.find(e => e.id === selectedId);

  return (
    <div className="fade-in">
      <div className="disclaimer-box" style={{ marginBottom: 16 }}>
        <Info size={13} style={{ flexShrink: 0, marginTop: 1 }} />
        <span>
          <strong>Heuristic simulation only.</strong> Moving virtual shelves estimates geometric metrics
          (walking distance, space utilization, and obstacle clearance) — it does NOT predict real customer behavior.
          All outputs are labeled as estimates. Field validation required before operational decisions.
        </span>
      </div>

      <div className="simulator-layout" style={{ gridTemplateColumns: '270px 1fr' }}>
        {/* Left panel */}
        <div className="simulator-panel">
          {/* Mode & Undo */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px' }}>
                Mode & History
              </div>
              <button
                className="sim-btn"
                style={{ padding: '3px 8px', fontSize: 11 }}
                onClick={undo}
                disabled={undoStack.length === 0}
                title="Undo last change"
              >
                <Undo size={11} /> Undo ({undoStack.length})
              </button>
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              <button className={`sim-btn${mode === 'select' ? ' active' : ''}`} onClick={() => setMode('select')}>
                <Move size={13} /> Select
              </button>
              <button className={`sim-btn${mode === 'add' ? ' active' : ''}`} onClick={() => setMode('add')}>
                <Plus size={13} /> Add
              </button>
            </div>
          </div>

          {/* Element types */}
          {mode === 'add' && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 8 }}>
                Element Type
              </div>
              <div className="element-type-grid">
                {ELEMENT_TYPES.map(t => (
                  <button
                    key={t.type}
                    className={`element-type-btn${activeType === t.type ? ' active' : ''}`}
                    onClick={() => setActiveType(t.type)}
                  >
                    <span style={{ fontSize: 18 }}>{t.icon}</span>
                    {t.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Selected element */}
          {selectedEl && (
            <div style={{ marginBottom: 16, background: 'rgba(255,255,255,0.02)', padding: 10, borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 8 }}>
                Selected: {selectedEl.label} ({selectedEl.element_type})
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: 11 }}>
                {['x','y','width','height'].map(field => (
                  <div key={field}>
                    <div style={{ color: 'var(--text-muted)', marginBottom: 3 }}>{field}</div>
                    <input
                      type="number"
                      className="input-field"
                      style={{ width: '100%' }}
                      value={selectedEl[field]}
                      onChange={e => {
                        const val = parseInt(e.target.value) || 0;
                        pushHistory();
                        setElements(prev => prev.map(el =>
                          el.id === selectedId ? { ...el, [field]: snapToGrid(val) } : el
                        ));
                        setValidationResult(null);
                      }}
                    />
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 8 }}>
                <div style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 3 }}>Label</div>
                <input
                  type="text"
                  className="input-field"
                  style={{ width: '100%' }}
                  value={selectedEl.label}
                  onChange={e => {
                    setElements(prev => prev.map(el =>
                      el.id === selectedId ? { ...el, label: e.target.value } : el
                    ));
                  }}
                />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 4, marginTop: 10 }}>
                <button className="sim-btn" style={{ padding: '4px 6px', fontSize: 11 }} onClick={rotateSelected} title="Rotate 90°">
                  <RotateCw size={11} /> 90°
                </button>
                <button className="sim-btn" style={{ padding: '4px 6px', fontSize: 11 }} onClick={duplicateSelected} title="Duplicate element">
                  <Copy size={11} /> Clone
                </button>
                <button className="sim-btn danger" style={{ padding: '4px 6px', fontSize: 11 }} onClick={deleteSelected} title="Delete element">
                  <Trash2 size={11} /> Del
                </button>
              </div>
            </div>
          )}

          {/* Layout name */}
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Proposed Layout Name</div>
            <input
              type="text"
              className="input-field"
              style={{ width: '100%' }}
              value={layoutName}
              onChange={e => setLayoutName(e.target.value)}
            />
          </div>

          {/* Direct Simulation & Validation actions */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <button className="sim-btn primary" onClick={simulateProposed} disabled={saving} style={{ fontWeight: 600 }}>
              <Play size={13} /> Simulate & Compare
            </button>
            <button className="sim-btn" onClick={validateGeometry} disabled={validating}>
              <CheckCircle2 size={13} /> {validating ? 'Validating...' : 'Validate Geometry'}
            </button>
            <button className="sim-btn success" onClick={() => saveLayout(false)} disabled={saving}>
              <Save size={13} /> {saving ? 'Saving...' : 'Save Proposed Layout'}
            </button>
            <button className="sim-btn" onClick={() => saveLayout(true)} disabled={saving}>
              <Save size={13} /> Overwrite Baseline
            </button>
            <div style={{ display: 'flex', gap: 6 }}>
              <button className="sim-btn" style={{ flex: 1 }} onClick={resetToBaseline} title="Load baseline layout into canvas">
                <RotateCcw size={12} /> Baseline
              </button>
              <button className="sim-btn" style={{ flex: 1 }} onClick={resetToDefault} title="Reset to standard template">
                <RotateCcw size={12} /> Default
              </button>
            </div>
            <button className="sim-btn" onClick={() => setShowLayouts(s => !s)}>
              <Layout size={13} /> {showLayouts ? 'Hide' : 'Browse'} Layouts
            </button>
          </div>

          {savedMsg && (
            <div style={{ marginTop: 10, fontSize: 12, color: savedMsg.startsWith('✓') ? '#10b981' : '#f59e0b', fontWeight: 600 }}>
              {savedMsg}
            </div>
          )}

          {/* Validation Result Box */}
          {validationResult && (
            <div style={{
              marginTop: 12, padding: 10, borderRadius: 6,
              background: validationResult.valid ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
              border: `1px solid ${validationResult.valid ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}`,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 700, color: validationResult.valid ? '#10b981' : '#ef4444' }}>
                {validationResult.valid ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
                {validationResult.valid ? 'Geometry Valid' : 'Geometry Issues Detected'}
              </div>
              {validationResult.errors?.map((err, i) => (
                <div key={i} style={{ fontSize: 11, color: '#ef4444', marginTop: 4 }}>• {err}</div>
              ))}
              {validationResult.warnings?.map((w, i) => (
                <div key={i} style={{ fontSize: 11, color: '#f59e0b', marginTop: 4 }}>• {w}</div>
              ))}
            </div>
          )}

          {/* Layouts browser */}
          {showLayouts && (
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 8 }}>SAVED LAYOUTS</div>
              {layouts.length === 0 ? (
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>No saved layouts</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {layouts.map(l => (
                    <button key={l.id} className="sim-btn" style={{ textAlign: 'left', justifyContent: 'flex-start' }}
                      onClick={() => loadLayout(l.id)}>
                      <Layout size={12} />
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 150 }}>{l.name}</span>
                      {l.is_baseline && <span style={{ fontSize: 10, marginLeft: 'auto', color: '#10b981' }}>BASE</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Stats */}
          <div style={{ marginTop: 16, padding: 10, background: 'rgba(255,255,255,0.03)', borderRadius: 8 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>Current Layout Stats</div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.8 }}>
              Elements: <strong>{elements.length}</strong><br />
              Shelves: <strong>{elements.filter(e => e.element_type === 'shelf').length}</strong><br />
              Checkouts: <strong>{elements.filter(e => e.element_type === 'checkout').length}</strong><br />
              Area used: <strong>{Math.round(elements.reduce((s, e) => s + e.width * e.height, 0) / (CANVAS_W * CANVAS_H) * 100)}%</strong><br />
              Overlap pairs: <strong style={{ color: overlapPairs.length > 0 ? '#ef4444' : '#10b981' }}>{overlapPairs.length}</strong>
            </div>
          </div>
        </div>

        {/* Canvas */}
        <div className="simulator-canvas-wrapper">
          {/* Overlap Collision Alert Banner */}
          {overlapPairs.length > 0 && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '10px 14px', marginBottom: 12,
              background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.3)',
              borderRadius: 6, color: '#fca5a5', fontSize: 12
            }}>
              <ShieldAlert size={18} style={{ color: '#ef4444', flexShrink: 0 }} />
              <div>
                <strong>Aisle Collision Warning:</strong> {overlapPairs.length} overlapping fixture pair(s) detected:
                {' '}{overlapPairs.map(p => `${p.labelA} ↔ ${p.labelB}`).join(', ')}.
                {' '}Overlaps obstruct customer walkable paths and increase route conflict.
              </div>
            </div>
          )}

          <div className="simulator-toolbar">
            <span style={{ fontSize: 12, color: 'var(--text-muted)', marginRight: 4 }}>
              Mode: <strong style={{ color: mode === 'add' ? '#6366f1' : 'var(--text-secondary)' }}>{mode === 'add' ? `Add ${activeType}` : 'Select & Move'}</strong>
            </span>
            {mode === 'add' && (
              <span style={{ fontSize: 11, color: 'var(--brand-accent)' }}>
                Click on canvas to place element
              </span>
            )}
            <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-muted)' }}>
              Canvas: {CANVAS_W}×{CANVAS_H}px · Grid: {GRID_SIZE}px Snapping
            </span>
          </div>

          <div style={{ flex: 1, overflow: 'auto' }}>
            <svg
              ref={svgRef}
              viewBox={`0 0 ${CANVAS_W} ${CANVAS_H}`}
              style={{
                width: '100%',
                minHeight: 400,
                display: 'block',
                cursor: mode === 'add' ? 'crosshair' : 'default',
                background: `
                  linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
                  linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)`,
                backgroundSize: `${GRID_SIZE}px ${GRID_SIZE}px`,
                backgroundColor: '#070c1a',
              }}
              onClick={handleCanvasClick}
            >
              {/* Store border */}
              <rect x="1" y="1" width={CANVAS_W-2} height={CANVAS_H-2}
                fill="none" stroke="rgba(99,102,241,0.15)" strokeWidth="2" rx="4"
                strokeDasharray="8 4" />

              {/* Elements */}
              {elements.map(el => {
                const typeInfo = ELEMENT_TYPES.find(t => t.type === el.element_type) || ELEMENT_TYPES[0];
                const isSelected = el.id === selectedId;
                const isColliding = collidingIds.has(el.id);

                return (
                  <g key={el.id}
                    transform={`translate(${el.x},${el.y}) rotate(${el.rotation || 0},${el.width/2},${el.height/2})`}
                    onMouseDown={e => handleElMouseDown(e, el.id)}
                    style={{ cursor: 'move', userSelect: 'none' }}
                  >
                    <rect
                      width={el.width} height={el.height}
                      rx="4"
                      fill={isColliding ? 'rgba(239,68,68,0.25)' : typeInfo.bg}
                      stroke={isSelected ? '#06b6d4' : isColliding ? '#ef4444' : typeInfo.color}
                      strokeWidth={isSelected ? 2.5 : isColliding ? 2 : 1.5}
                      strokeDasharray={isColliding ? '4 2' : undefined}
                      filter={isSelected ? 'drop-shadow(0 0 8px rgba(6,182,212,0.5))' : isColliding ? 'drop-shadow(0 0 8px rgba(239,68,68,0.5))' : undefined}
                    />
                    <text
                      x={el.width / 2} y={el.height / 2 - 6}
                      textAnchor="middle"
                      fill="white"
                      fontSize="16"
                      style={{ pointerEvents: 'none' }}
                    >
                      {typeInfo.icon}
                    </text>
                    <text
                      x={el.width / 2} y={el.height / 2 + 12}
                      textAnchor="middle"
                      fill="rgba(255,255,255,0.85)"
                      fontSize={Math.max(8, Math.min(12, el.width / 7))}
                      style={{ pointerEvents: 'none', fontWeight: isColliding ? 'bold' : 'normal' }}
                    >
                      {el.label}
                    </text>
                    {/* Collision Indicator mark */}
                    {isColliding && (
                      <circle
                        cx={el.width - 8} cy={8} r={5}
                        fill="#ef4444"
                      />
                    )}
                    {/* Resize handle */}
                    {isSelected && (
                      <rect
                        x={el.width - 8} y={el.height - 8}
                        width={10} height={10}
                        rx="2"
                        fill="#06b6d4"
                        style={{ cursor: 'se-resize' }}
                        onMouseDown={e => { e.stopPropagation(); handleResizeMouseDown(e, el.id); }}
                      />
                    )}
                  </g>
                );
              })}
            </svg>
          </div>

          {/* Legend */}
          <div style={{ padding: '8px 16px', borderTop: '1px solid var(--border-subtle)', display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
            {ELEMENT_TYPES.map(t => (
              <div key={t.type} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'var(--text-muted)' }}>
                <div style={{ width: 10, height: 10, borderRadius: 2, background: t.color, opacity: 0.7 }} />
                {t.label}
              </div>
            ))}
            <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#fca5a5' }}>
              <div style={{ width: 10, height: 10, borderRadius: 2, border: '1px dashed #ef4444', background: 'rgba(239,68,68,0.3)' }} />
              Overlap Collision
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
