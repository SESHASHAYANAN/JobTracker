import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Filters } from '../types';

interface SidebarProps {
  filters: Filters;
  onFilterChange: (f: Filters) => void;
  total: number;
}

const ROLES = ['', 'AI/ML', 'Engineering', 'Frontend', 'Backend', 'DevOps', 'Mobile', 'Design', 'Data', 'GTM', 'Ops', 'Cybersecurity', 'Blockchain'];
const LEVELS = ['', 'New Grad', 'Intern', 'Entry', 'Mid', 'Senior'];
const VISA = ['', 'Yes', 'No', 'Unknown'];
const COUNTRIES = ['', 'US', 'UK', 'India', 'Canada', 'EU', 'France', 'Germany', 'Netherlands', 'Australia', 'Remote'];
const STAGES = ['', 'Seed', 'Series A', 'Series B', 'Series C', 'Series D', 'Series E', 'Series F', 'Late Stage', 'Growth', 'Public'];
const VCS = ['', 'YC', 'a16z', 'Sequoia', 'Pearl', 'Lightspeed', 'Bessemer', 'Founders Fund', 'Tiger Global', 'Accel', 'Insight Partners', 'SoftBank', 'Prosus', 'Temasek', 'Khosla Ventures', 'Warburg Pincus'];
const BATCHES = ['', 'W25', 'S24', 'W24', 'S23'];
const TEAM_SIZES = ['', '1-10', '10-50', '50-200', '200+'];

function SelectFilter({
  id,
  label,
  value,
  options,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <div className="mb-4">
      <label
        htmlFor={id}
        className="block text-xs font-semibold mb-1.5 uppercase tracking-wider"
        style={{ color: 'var(--color-muted)' }}
      >
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 rounded-lg text-sm border outline-none cursor-pointer"
        style={{
          backgroundColor: 'var(--color-card)',
          color: 'var(--color-text)',
          borderColor: 'var(--color-border)',
        }}
      >
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt || 'All'}
          </option>
        ))}
      </select>
    </div>
  );
}

function ToggleFilter({
  id,
  label,
  checked,
  onChange,
}: {
  id: string;
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="mb-2 flex items-center justify-between px-1">
      <label htmlFor={id} className="text-xs font-medium cursor-pointer" style={{ color: 'var(--color-text)' }}>
        {label}
      </label>
      <button
        id={id}
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className="sidebar-toggle-switch"
        style={{
          backgroundColor: checked ? 'var(--color-accent)' : 'var(--color-border)',
        }}
      >
        <span
          className="sidebar-toggle-knob"
          style={{ transform: checked ? 'translateX(14px)' : 'translateX(1px)' }}
        />
      </button>
    </div>
  );
}

export default function Sidebar({ filters, onFilterChange, total }: SidebarProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const update = (key: keyof Filters, val: string) => {
    onFilterChange({ ...filters, [key]: val || undefined });
  };

  const sidebar = (
    <div className="p-4 space-y-1">
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-sm font-bold uppercase tracking-wider" style={{ color: 'var(--color-text)' }}>
          Filters
        </h2>
        <span
          className="text-xs px-2 py-1 rounded-full font-medium"
          style={{ backgroundColor: 'var(--color-accent)', color: '#fff' }}
        >
          {total} jobs
        </span>
      </div>


      {/* \u2500\u2500 Standard Filters \u2500\u2500 */}
      <SelectFilter id="filter-role" label="Role" value={filters.role || ''} options={ROLES} onChange={(v) => update('role', v)} />
      <SelectFilter id="filter-level" label="Level" value={filters.level || ''} options={LEVELS} onChange={(v) => update('level', v)} />
      <SelectFilter id="filter-visa" label="Visa Sponsorship" value={filters.visa || ''} options={VISA} onChange={(v) => update('visa', v)} />
      <SelectFilter id="filter-country" label="Country" value={filters.country || ''} options={COUNTRIES} onChange={(v) => update('country', v)} />
      <SelectFilter id="filter-stage" label="Stage" value={filters.stage || ''} options={STAGES} onChange={(v) => update('stage', v)} />
      <SelectFilter id="filter-vc" label="VC Backer" value={filters.vc || ''} options={VCS} onChange={(v) => update('vc', v)} />
      <SelectFilter id="filter-batch" label="YC Batch" value={filters.batch || ''} options={BATCHES} onChange={(v) => update('batch', v)} />
      <SelectFilter id="filter-teamsize" label="Team Size" value={filters.team_size_bucket || ''} options={TEAM_SIZES} onChange={(v) => update('team_size_bucket', v)} />

      <div className="mb-4">
        <label
          htmlFor="filter-founder"
          className="block text-xs font-semibold mb-1.5 uppercase tracking-wider"
          style={{ color: 'var(--color-muted)' }}
        >
          Founder Name
        </label>
        <input
          id="filter-founder"
          type="text"
          placeholder="Search founders..."
          value={filters.founder_name || ''}
          onChange={(e) => update('founder_name', e.target.value)}
          className="w-full px-3 py-2 rounded-lg text-sm border outline-none"
          style={{
            backgroundColor: 'var(--color-card)',
            color: 'var(--color-text)',
            borderColor: 'var(--color-border)',
          }}
        />
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile toggle */}
      <button
        id="sidebar-toggle"
        onClick={() => setMobileOpen(!mobileOpen)}
        className="lg:hidden fixed bottom-4 left-4 z-50 w-12 h-12 rounded-full flex items-center justify-center shadow-lg"
        style={{ backgroundColor: 'var(--color-accent)', color: '#fff' }}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {/* Desktop sidebar */}
      <aside
        className="hidden lg:block w-64 flex-shrink-0 border-r overflow-y-auto"
        style={{
          borderColor: 'var(--color-border)',
          backgroundColor: 'var(--color-bg)',
          height: 'calc(100vh - 57px)',
          position: 'sticky',
          top: '57px',
        }}
      >
        {sidebar}
      </aside>

      {/* Mobile sidebar */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.5 }}
              exit={{ opacity: 0 }}
              className="lg:hidden fixed inset-0 bg-black z-40"
              onClick={() => setMobileOpen(false)}
            />
            <motion.aside
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: 'tween', duration: 0.25 }}
              className="lg:hidden fixed left-0 top-0 bottom-0 w-72 z-50 overflow-y-auto border-r"
              style={{
                backgroundColor: 'var(--color-bg)',
                borderColor: 'var(--color-border)',
              }}
            >
              <div className="flex justify-end p-3">
                <button
                  onClick={() => setMobileOpen(false)}
                  className="p-2 rounded-lg"
                  style={{ color: 'var(--color-text)' }}
                >
                  ✕
                </button>
              </div>
              {sidebar}
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
