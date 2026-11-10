// =============================================================================
// Khan Parcel — Logistics Web Portal (Dispatcher & Business)
// =============================================================================

import React, { useState, useEffect, useRef } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Battery,
  Building,
  CheckCircle2,
  Clock,
  Compass,
  CreditCard,
  DollarSign,
  Download,
  FileCheck,
  FileText,
  Filter,
  Layers,
  LogOut,
  MapPin,
  Bike,
  Navigation,
  Package,
  Phone,
  Plus,
  RefreshCw,
  Search,
  ShieldAlert,
  Star,
  TrendingUp,
  Truck,
  Upload,
  User,
  Users,
  X,
  XCircle,
} from 'lucide-react';
import { apiFetch, tokenStorage } from './api';

// Seed initial coordinates (Islamabad center)
const DEFAULT_CENTER = [33.6844, 73.0479];

export default function App() {
  const [activeTab, setActiveTab] = useState('dispatch');
  const [user, setUser] = useState(tokenStorage.getUser() || { name: 'Operations Dispatcher', role: 'ADMIN' });
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  // Stats state
  const [stats, setStats] = useState({
    active_orders: 8,
    today_total_orders: 142,
    today_delivered_orders: 126,
    today_cancelled_orders: 8,
    completion_rate_pct: 94.0,
    today_gmv_pkr: '48,650.00',
    fleet: { total_online: 24, available: 18, busy: 6 },
    active_sos_alerts: 0,
    active_surge_hexagons: 3,
  });

  // Orders state
  const [orders, setOrders] = useState([
    {
      id: 'ord-1',
      order_number: 'KP-20261014-9A4B',
      customer_name: 'Ahmed Malik',
      customer_phone: '+923001234567',
      rider_name: 'Zubair Khan',
      status: 'PICKED_UP',
      vehicle_type: 'BIKE',
      fare_amount: '320.00',
      cod_amount: '1,500.00',
      total_amount: '320.00',
      pickup_address: 'F-7 Markaz, Islamabad',
      dropoff_address: 'G-11/3, Islamabad',
      pickup_lat: 33.7214,
      pickup_lng: 73.0564,
      dropoff_lat: 33.6688,
      dropoff_lng: 72.9982,
      created_at: '2026-10-14 15:10:00',
    },
    {
      id: 'ord-2',
      order_number: 'KP-20261014-5F2C',
      customer_name: 'Sana Tariq',
      customer_phone: '+923219876543',
      rider_name: null,
      status: 'SEARCHING_RIDER',
      vehicle_type: 'BIKE',
      fare_amount: '210.00',
      cod_amount: '0.00',
      total_amount: '210.00',
      pickup_address: 'Blue Area, Jinnah Ave, Islamabad',
      dropoff_address: 'I-8/4, Islamabad',
      pickup_lat: 33.7088,
      pickup_lng: 73.0552,
      dropoff_lat: 33.6732,
      dropoff_lng: 73.0784,
      created_at: '2026-10-14 15:22:00',
    },
    {
      id: 'ord-3',
      order_number: 'KP-20261014-88E1',
      customer_name: 'Metro Pharmacy',
      customer_phone: '+923334445555',
      rider_name: 'Hamza Farooq',
      status: 'RIDER_ARRIVED_PICKUP',
      vehicle_type: 'BIKE',
      fare_amount: '180.00',
      cod_amount: '3,200.00',
      total_amount: '180.00',
      pickup_address: 'Saddar, Rawalpindi',
      dropoff_address: 'Bahria Town Phase 4, Rawalpindi',
      pickup_lat: 33.5971,
      pickup_lng: 73.0538,
      dropoff_lat: 33.5412,
      dropoff_lng: 73.1118,
      created_at: '2026-10-14 15:15:00',
    },
  ]);

  // Riders state
  const [riders, setRiders] = useState([
    {
      id: 'rd-1',
      name: 'Zubair Khan',
      phone: '+923015551234',
      vehicle_type: 'BIKE',
      plate: 'ICT-LE-4192',
      status: 'BUSY',
      is_online: true,
      review_status: 'APPROVED',
      rating: '4.92',
      battery: 84,
      active_orders: 1,
      lat: 33.7050,
      lng: 73.0420,
    },
    {
      id: 'rd-2',
      name: 'Hamza Farooq',
      phone: '+923456667890',
      vehicle_type: 'BIKE',
      plate: 'RWP-KH-9012',
      status: 'BUSY',
      is_online: true,
      review_status: 'APPROVED',
      rating: '4.85',
      battery: 62,
      active_orders: 1,
      lat: 33.5950,
      lng: 73.0510,
    },
    {
      id: 'rd-3',
      name: 'Bilal Mustafa',
      phone: '+923127778899',
      vehicle_type: 'CAR',
      plate: 'ICT-AW-510',
      status: 'AVAILABLE',
      is_online: true,
      review_status: 'APPROVED',
      rating: '4.98',
      battery: 95,
      active_orders: 0,
      lat: 33.6920,
      lng: 73.0280,
    },
    {
      id: 'rd-4',
      name: 'Usman Ali',
      phone: '+923008889900',
      vehicle_type: 'BIKE',
      plate: 'RWP-AB-1234',
      status: 'OFFLINE',
      is_online: false,
      review_status: 'PENDING_REVIEW',
      rating: '5.00',
      battery: 40,
      active_orders: 0,
      lat: 33.6800,
      lng: 73.0400,
    },
  ]);

  // Selected items & modals
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [assignModalOrder, setAssignModalOrder] = useState(null);
  const [activeSOS, setActiveSOS] = useState(null);

  // Business quote state
  const [quoteInput, setQuoteInput] = useState({
    pickup_address: 'Sector F-6/1, Islamabad',
    dropoff_address: 'Sector H-12, NUST, Islamabad',
    pickup_lat: 33.7297,
    pickup_lng: 73.0746,
    dropoff_lat: 33.6425,
    dropoff_lng: 72.9930,
    vehicle_type: 'BIKE',
    cod_amount: '0',
    recipient_name: 'Taimoor Sheikh',
    recipient_phone: '+923005556677',
  });
  const [calculatedQuote, setCalculatedQuote] = useState(null);
  const [isQuoting, setIsQuoting] = useState(false);

  // Bulk Upload state
  const [bulkFile, setBulkFile] = useState(null);
  const [bulkProgress, setBulkProgress] = useState(null);

  // Initial load from backend API if running
  useEffect(() => {
    fetchBackendData();
    const interval = setInterval(fetchBackendData, 15000);
    return () => clearInterval(interval);
  }, []);

  async function fetchBackendData() {
    try {
      const statsRes = await apiFetch('/ops/dashboard/');
      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }
      const ordersRes = await apiFetch('/orders/');
      if (ordersRes.ok) {
        const ordersData = await ordersRes.json();
        if (Array.isArray(ordersData.results)) setOrders(ordersData.results);
      }
      const fleetRes = await apiFetch('/ops/fleet/live/');
      if (fleetRes.ok) {
        const fleetData = await fleetRes.json();
        if (Array.isArray(fleetData)) setRiders(fleetData);
      }
    } catch (e) {
      // Backend offline, fallback mock mode persists
    }
  }

  // Handle Quote Calculation
  async function handleCalculateQuote(e) {
    e.preventDefault();
    setIsQuoting(true);
    try {
      const res = await apiFetch('/pricing/quote/', {
        method: 'POST',
        body: JSON.stringify({
          pickup_lat: parseFloat(quoteInput.pickup_lat),
          pickup_lng: parseFloat(quoteInput.pickup_lng),
          dropoff_lat: parseFloat(quoteInput.dropoff_lat),
          dropoff_lng: parseFloat(quoteInput.dropoff_lng),
          pickup_address: quoteInput.pickup_address,
          dropoff_address: quoteInput.dropoff_address,
          vehicle_type: quoteInput.vehicle_type,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setCalculatedQuote(data);
      } else {
        // Fallback local quote
        setCalculatedQuote({
          id: 'quote-mock-1',
          distance_km: '11.8',
          duration_minutes: '24',
          base_price: '100.00',
          distance_price: '245.00',
          surge_amount: '0.00',
          discount_amount: '0.00',
          total_price: '345.00',
        });
      }
    } catch {
      setCalculatedQuote({
        id: 'quote-mock-1',
        distance_km: '11.8',
        duration_minutes: '24',
        base_price: '100.00',
        distance_price: '245.00',
        surge_amount: '0.00',
        discount_amount: '0.00',
        total_price: '345.00',
      });
    } finally {
      setIsQuoting(false);
    }
  }

  // Manual Dispatch Assignment
  async function handleAssignRider(riderId) {
    if (!assignModalOrder) return;
    try {
      await apiFetch('/dispatch/manual-assign/', {
        method: 'POST',
        body: JSON.stringify({
          order_id: assignModalOrder.id,
          rider_id: riderId,
        }),
      });
    } catch {}

    // Update UI state
    const assignedRider = riders.find((r) => r.id === riderId);
    setOrders((prev) =>
      prev.map((o) =>
        o.id === assignModalOrder.id
          ? { ...o, status: 'RIDER_ASSIGNED', rider_name: assignedRider ? assignedRider.name : 'Assigned' }
          : o
      )
    );
    setAssignModalOrder(null);
  }

  // KYC Approval
  async function handleKYCAction(riderId, approve) {
    setRiders((prev) =>
      prev.map((r) =>
        r.id === riderId ? { ...r, review_status: approve ? 'APPROVED' : 'REJECTED' } : r
      )
    );
  }

  return (
    <div className="flex h-screen w-full flex-col bg-slate-950 font-sans text-slate-100">
      {/* ─── Top Header & SOS Bar ────────────────────────────────────────── */}
      <header className="z-20 flex h-16 shrink-0 items-center justify-between border-b border-slate-800 bg-slate-900/90 px-6 backdrop-blur-md">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-sky-600 to-cyan-400 font-black text-white shadow-lg shadow-sky-500/20">
              <Package className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-extrabold tracking-tight text-white">
                  KHAN<span className="text-sky-400">PARCEL</span>
                </span>
                <span className="rounded-full bg-sky-500/10 px-2 py-0.5 text-xs font-semibold text-sky-400 ring-1 ring-inset ring-sky-500/20">
                  CONTROL ROOM
                </span>
              </div>
              <p className="text-[11px] font-medium text-slate-400">Real-Time Dispatch & Logistics Engine</p>
            </div>
          </div>

          {/* Realtime Live Pulse */}
          <div className="ml-6 flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-1.5 text-xs">
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500"></span>
            </span>
            <span className="font-mono text-emerald-400">LIVE FEED</span>
            <span className="text-slate-500">|</span>
            <span className="text-slate-300">{stats.fleet.total_online} Riders Online</span>
          </div>
        </div>

        {/* SOS Emergency Banner if active */}
        {activeSOS && (
          <div className="flex animate-pulse items-center gap-3 rounded-lg bg-rose-600/20 px-4 py-1.5 text-sm font-semibold text-rose-400 ring-1 ring-rose-500">
            <ShieldAlert className="h-5 w-5 text-rose-500" />
            <span>EMERGENCY SOS: {activeSOS.rider_name} ({activeSOS.reason})</span>
            <button
              onClick={() => setActiveSOS(null)}
              className="rounded bg-rose-600 px-2 py-0.5 text-xs text-white hover:bg-rose-500"
            >
              Resolve
            </button>
          </div>
        )}

        {/* User Info & Actions */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => {
              setActiveSOS({
                rider_name: 'Zubair Khan',
                reason: 'Accident on Expressway',
              });
            }}
            className="flex items-center gap-1.5 rounded-lg border border-rose-500/40 bg-rose-950/30 px-3 py-1.5 text-xs font-semibold text-rose-300 transition hover:bg-rose-900/50"
          >
            <AlertTriangle className="h-3.5 w-3.5" />
            Simulate SOS
          </button>

          <div className="flex items-center gap-3 border-l border-slate-800 pl-4">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-800 text-xs font-bold text-sky-400">
              {user.name.charAt(0)}
            </div>
            <div className="text-right">
              <div className="text-xs font-bold text-slate-200">{user.name}</div>
              <div className="text-[10px] text-sky-400">{user.role}</div>
            </div>
          </div>
        </div>
      </header>

      {/* ─── Navigation Tabs ─────────────────────────────────────────────── */}
      <div className="flex shrink-0 items-center gap-1 border-b border-slate-800 bg-slate-900/50 px-6 py-2">
        {[
          { id: 'dispatch', label: 'Live Dispatch Map', icon: Navigation },
          { id: 'orders', label: 'Orders Matrix', icon: Package },
          { id: 'fleet', label: 'Fleet & KYC', icon: Users },
          { id: 'financials', label: 'Financials & COD', icon: DollarSign },
          { id: 'business', label: 'Corporate Portal', icon: Building },
          { id: 'surge', label: 'Surge & Tariffs', icon: TrendingUp },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 rounded-lg px-3.5 py-2 text-xs font-semibold transition ${
                isActive
                  ? 'bg-sky-500/10 text-sky-400 ring-1 ring-sky-500/30'
                  : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
              {tab.id === 'orders' && (
                <span className="rounded-full bg-slate-800 px-1.5 py-0.2 text-[10px] text-slate-400">
                  {orders.length}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* ─── Main Content Area ───────────────────────────────────────────── */}
      <main className="relative flex-1 overflow-hidden">
        {/* TAB 1: LIVE DISPATCH ROOM */}
        {activeTab === 'dispatch' && (
          <div className="flex h-full w-full">
            {/* Left: Dispatch Order Queue & Controls */}
            <div className="flex w-96 flex-col border-r border-slate-800 bg-slate-900/40">
              <div className="border-b border-slate-800 p-4">
                <h2 className="text-sm font-bold text-white">Unassigned Order Queue</h2>
                <p className="text-xs text-slate-400">Orders actively matching or pending dispatch</p>
              </div>

              <div className="flex-1 space-y-3 overflow-y-auto p-4">
                {orders
                  .filter((o) => o.status === 'SEARCHING_RIDER' || !o.rider_name)
                  .map((order) => (
                    <div
                      key={order.id}
                      className="group rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 transition hover:border-amber-500/60"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-bold text-amber-400">
                          {order.order_number}
                        </span>
                        <span className="rounded-full bg-amber-500/20 px-2 py-0.5 text-[10px] font-bold text-amber-300">
                          MATCHING
                        </span>
                      </div>

                      <div className="mt-3 space-y-1.5 text-xs text-slate-300">
                        <div className="flex items-center gap-1.5">
                          <MapPin className="h-3.5 w-3.5 shrink-0 text-emerald-400" />
                          <span className="truncate">{order.pickup_address}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <MapPin className="h-3.5 w-3.5 shrink-0 text-rose-400" />
                          <span className="truncate">{order.dropoff_address}</span>
                        </div>
                      </div>

                      <div className="mt-3 flex items-center justify-between border-t border-slate-800/80 pt-2 text-xs">
                        <span className="font-bold text-white">{order.fare_amount} PKR</span>
                        <button
                          onClick={() => setAssignModalOrder(order)}
                          className="rounded-lg bg-sky-600 px-3 py-1 font-semibold text-white shadow transition hover:bg-sky-500"
                        >
                          Manual Assign
                        </button>
                      </div>
                    </div>
                  ))}

                {orders.filter((o) => o.status === 'SEARCHING_RIDER' || !o.rider_name).length === 0 && (
                  <div className="py-12 text-center text-xs text-slate-500">
                    <CheckCircle2 className="mx-auto mb-2 h-8 w-8 text-emerald-500/50" />
                    All active orders are assigned to riders.
                  </div>
                )}
              </div>

              {/* Bottom Quick KPI panel */}
              <div className="border-t border-slate-800 bg-slate-950 p-4">
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded-lg bg-slate-900 p-2.5">
                    <span className="text-slate-400">Available Fleet</span>
                    <p className="mt-0.5 text-lg font-bold text-emerald-400">{stats.fleet.available}</p>
                  </div>
                  <div className="rounded-lg bg-slate-900 p-2.5">
                    <span className="text-slate-400">On Delivery</span>
                    <p className="mt-0.5 text-lg font-bold text-amber-400">{stats.fleet.busy}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Right: Live Interactive Dispatch Map Container */}
            <div className="relative flex-1 bg-slate-950">
              <iframe
                title="Live Dispatch Radar"
                className="h-full w-full border-none"
                srcDoc={`<!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    body, html, #map { margin: 0; padding: 0; height: 100%; width: 100%; background: #090d16; }
    .rider-pin { background: #0284c7; color: white; padding: 4px 8px; border-radius: 999px; font-weight: bold; font-size: 11px; border: 2px solid white; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
    .order-pin { background: #10b981; color: white; padding: 4px 8px; border-radius: 999px; font-weight: bold; font-size: 11px; border: 2px solid white; }
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    const map = L.map('map').setView([33.6844, 73.0479], 13);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; CartoDB'
    }).addTo(map);

    const riders = ${JSON.stringify(riders)};
    riders.forEach(r => {
      const color = r.status === 'AVAILABLE' ? '#10b981' : '#f59e0b';
      const marker = L.circleMarker([r.lat, r.lng], {
        radius: 8,
        fillColor: color,
        color: '#ffffff',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.9
      }).addTo(map);
      marker.bindPopup('<b>' + r.name + '</b><br>Status: ' + r.status + '<br>Vehicle: ' + r.vehicle_type + '<br>⭐ ' + r.rating);
    });

    const orders = ${JSON.stringify(orders)};
    orders.forEach(o => {
      L.marker([o.pickup_lat, o.pickup_lng]).addTo(map).bindPopup('<b>Order: ' + o.order_number + '</b><br>Pickup: ' + o.pickup_address);
      L.marker([o.dropoff_lat, o.dropoff_lng]).addTo(map).bindPopup('<b>Order: ' + o.order_number + '</b><br>Dropoff: ' + o.dropoff_address);
    });
  </script>
</body>
</html>`}
              />

              {/* Map Floating Overlay Card */}
              <div className="glass-card absolute bottom-6 right-6 z-10 w-80 rounded-2xl p-4 shadow-2xl">
                <div className="flex items-center justify-between pb-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Fleet Telemetry</span>
                  <span className="flex items-center gap-1 text-[11px] text-emerald-400">
                    <Activity className="h-3 w-3" /> 15s Heartbeat
                  </span>
                </div>
                <div className="space-y-2 border-t border-slate-800 pt-2 text-xs">
                  {riders.slice(0, 3).map((r) => (
                    <div key={r.id} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div
                          className={`h-2 w-2 rounded-full ${
                            r.status === 'AVAILABLE' ? 'bg-emerald-400' : 'bg-amber-400'
                          }`}
                        />
                        <span className="font-medium text-slate-200">{r.name}</span>
                      </div>
                      <div className="flex items-center gap-2 font-mono text-[11px] text-slate-400">
                        <Battery className="h-3 w-3 text-sky-400" /> {r.battery}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: ORDERS MATRIX */}
        {activeTab === 'orders' && (
          <div className="flex h-full flex-col overflow-y-auto p-6">
            {/* KPI Cards */}
            <div className="grid grid-cols-4 gap-4">
              <div className="glass-card rounded-2xl p-5">
                <span className="text-xs font-semibold text-slate-400">Today's Orders</span>
                <p className="mt-1 text-2xl font-extrabold text-white">{stats.today_total_orders}</p>
                <span className="mt-1 flex items-center gap-1 text-xs text-emerald-400">
                  <TrendingUp className="h-3.5 w-3.5" /> +14.2% vs yesterday
                </span>
              </div>
              <div className="glass-card rounded-2xl p-5">
                <span className="text-xs font-semibold text-slate-400">Completed (Delivered)</span>
                <p className="mt-1 text-2xl font-extrabold text-emerald-400">{stats.today_delivered_orders}</p>
                <span className="mt-1 text-xs text-slate-400">Completion: {stats.completion_rate_pct}%</span>
              </div>
              <div className="glass-card rounded-2xl p-5">
                <span className="text-xs font-semibold text-slate-400">In Transit Now</span>
                <p className="mt-1 text-2xl font-extrabold text-sky-400">{stats.active_orders}</p>
                <span className="mt-1 text-xs text-slate-400">Avg ETA: 18.5 mins</span>
              </div>
              <div className="glass-card rounded-2xl p-5">
                <span className="text-xs font-semibold text-slate-400">Gross Merchandise Value</span>
                <p className="mt-1 text-2xl font-extrabold text-cyan-400">{stats.today_gmv_pkr} PKR</p>
                <span className="mt-1 text-xs text-slate-400">Platform Share: 20%</span>
              </div>
            </div>

            {/* Orders Table */}
            <div className="glass-card mt-6 rounded-2xl p-5">
              <div className="flex items-center justify-between pb-4">
                <h3 className="text-base font-bold text-white">Live Orders Stream</h3>
                <div className="flex items-center gap-2">
                  <div className="relative">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                    <input
                      type="text"
                      placeholder="Search order, customer, phone..."
                      className="rounded-xl border border-slate-700 bg-slate-900/80 py-2 pl-9 pr-4 text-xs text-white placeholder-slate-500 focus:border-sky-500 focus:outline-none"
                    />
                  </div>
                  <a
                    href="/api/v1/ops/export/orders/"
                    className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800 px-3.5 py-2 text-xs font-semibold text-slate-200 transition hover:bg-slate-700"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Export CSV
                  </a>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-800 bg-slate-900/50 text-slate-400">
                    <tr>
                      <th className="py-3 pl-4">Order #</th>
                      <th className="py-3">Customer</th>
                      <th className="py-3">Rider</th>
                      <th className="py-3">Vehicle</th>
                      <th className="py-3">Status</th>
                      <th className="py-3">Total Fare</th>
                      <th className="py-3">COD Amount</th>
                      <th className="py-3">Created</th>
                      <th className="py-3 pr-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-medium">
                    {orders.map((o) => (
                      <tr key={o.id} className="transition hover:bg-slate-900/40">
                        <td className="py-3.5 pl-4 font-mono font-bold text-sky-400">{o.order_number}</td>
                        <td className="py-3.5">
                          <div className="text-white">{o.customer_name}</div>
                          <div className="text-[11px] text-slate-500">{o.customer_phone}</div>
                        </td>
                        <td className="py-3.5">
                          {o.rider_name ? (
                            <span className="text-slate-200">{o.rider_name}</span>
                          ) : (
                            <span className="text-amber-400 italic">Unassigned</span>
                          )}
                        </td>
                        <td className="py-3.5">
                          <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-bold text-slate-300">
                            {o.vehicle_type}
                          </span>
                        </td>
                        <td className="py-3.5">
                          <span
                            className={`rounded-full px-2.5 py-1 text-[10px] font-bold ${
                              o.status === 'DELIVERED'
                                ? 'bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/30'
                                : o.status === 'PICKED_UP'
                                ? 'bg-sky-500/10 text-sky-400 ring-1 ring-sky-500/30'
                                : o.status === 'SEARCHING_RIDER'
                                ? 'bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/30'
                                : 'bg-slate-700 text-slate-300'
                            }`}
                          >
                            {o.status.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="py-3.5 font-bold text-white">{o.fare_amount} PKR</td>
                        <td className="py-3.5 font-bold text-cyan-400">{o.cod_amount} PKR</td>
                        <td className="py-3.5 text-slate-400">{o.created_at}</td>
                        <td className="py-3.5 pr-4 text-right">
                          <button
                            onClick={() => setSelectedOrder(o)}
                            className="rounded-lg bg-slate-800 px-2.5 py-1 text-[11px] font-semibold text-slate-300 transition hover:bg-slate-700 hover:text-white"
                          >
                            Details
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: FLEET & KYC REVIEW */}
        {activeTab === 'fleet' && (
          <div className="flex h-full flex-col overflow-y-auto p-6">
            <div className="flex items-center justify-between pb-4">
              <div>
                <h2 className="text-lg font-bold text-white">Rider Fleet & KYC Review</h2>
                <p className="text-xs text-slate-400">Driver verification, document compliance, and shift tracking</p>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {riders.map((r) => (
                <div key={r.id} className="glass-card rounded-2xl p-5">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-800 font-black text-sky-400">
                        {r.name.charAt(0)}
                      </div>
                      <div>
                        <div className="text-sm font-bold text-white">{r.name}</div>
                        <div className="text-xs text-slate-400">{r.phone}</div>
                        <div className="mt-1 flex items-center gap-2 text-xs">
                          <span className="font-mono text-slate-300">{r.plate}</span>
                          <span className="text-slate-600">•</span>
                          <span className="flex items-center gap-1 text-amber-400 font-bold">
                            <Star className="h-3 w-3 fill-amber-400" /> {r.rating}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="text-right">
                      <span
                        className={`rounded-full px-2.5 py-1 text-[10px] font-bold ${
                          r.review_status === 'APPROVED'
                            ? 'bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/30'
                            : 'bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/30'
                        }`}
                      >
                        {r.review_status}
                      </span>
                      <div className="mt-2 flex items-center justify-end gap-1 text-xs text-slate-400">
                        <Battery className="h-3.5 w-3.5 text-sky-400" /> {r.battery}%
                      </div>
                    </div>
                  </div>

                  {/* KYC Action panel if pending */}
                  {r.review_status === 'PENDING_REVIEW' && (
                    <div className="mt-4 rounded-xl border border-amber-500/30 bg-amber-500/5 p-3 text-xs">
                      <span className="font-bold text-amber-400">KYC Documents Submitted</span>
                      <p className="mt-1 text-slate-300">CNIC front/back & Driving License attached.</p>
                      <div className="mt-3 flex gap-2">
                        <button
                          onClick={() => handleKYCAction(r.id, true)}
                          className="rounded-lg bg-emerald-600 px-3 py-1 font-semibold text-white transition hover:bg-emerald-500"
                        >
                          Approve Driver
                        </button>
                        <button
                          onClick={() => handleKYCAction(r.id, false)}
                          className="rounded-lg bg-rose-600 px-3 py-1 font-semibold text-white transition hover:bg-rose-500"
                        >
                          Reject
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 4: FINANCIALS & COD */}
        {activeTab === 'financials' && (
          <div className="flex h-full flex-col overflow-y-auto p-6">
            <h2 className="text-lg font-bold text-white">Cash-on-Delivery & Financial Ledger</h2>
            <p className="text-xs text-slate-400">Driver remittances, bank deposit slips, and platform commission reconciliation</p>

            <div className="mt-5 grid grid-cols-3 gap-4">
              <div className="glass-card rounded-2xl p-5">
                <span className="text-xs text-slate-400 font-semibold">Total COD Cash Collected</span>
                <p className="mt-1 text-2xl font-black text-cyan-400">128,450.00 PKR</p>
                <span className="mt-1 text-xs text-slate-400">Across 86 orders today</span>
              </div>
              <div className="glass-card rounded-2xl p-5">
                <span className="text-xs text-slate-400 font-semibold">Verified Bank Remittances</span>
                <p className="mt-1 text-2xl font-black text-emerald-400">92,000.00 PKR</p>
                <span className="mt-1 text-xs text-slate-400">Deposited into corporate account</span>
              </div>
              <div className="glass-card rounded-2xl p-5">
                <span className="text-xs text-slate-400 font-semibold">Pending Rider Deposits</span>
                <p className="mt-1 text-2xl font-black text-amber-400">36,450.00 PKR</p>
                <span className="mt-1 text-xs text-slate-400">Holding in rider custody</span>
              </div>
            </div>

            {/* Payout & Remittance Review Stream */}
            <div className="glass-card mt-6 rounded-2xl p-5">
              <div className="flex items-center justify-between pb-4">
                <h3 className="text-sm font-bold text-white">Pending Rider Bank Remittance Slips</h3>
                <a
                  href="/api/v1/ops/export/ledger/"
                  className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800 px-3.5 py-2 text-xs font-semibold text-slate-200 transition hover:bg-slate-700"
                >
                  <Download className="h-3.5 w-3.5" /> Export Ledger CSV
                </a>
              </div>

              <div className="space-y-3">
                {[
                  {
                    rider: 'Zubair Khan',
                    amount: '14,500.00 PKR',
                    bank: 'Habib Bank Ltd (HBL)',
                    ref: 'HBL-FT-98124891',
                    date: 'Today 14:10',
                  },
                  {
                    rider: 'Hamza Farooq',
                    amount: '8,200.00 PKR',
                    bank: 'Meezan Bank',
                    ref: 'MEZN-TR-552190',
                    date: 'Today 13:45',
                  },
                ].map((slip, i) => (
                  <div key={i} className="flex items-center justify-between rounded-xl bg-slate-900/60 p-4 text-xs">
                    <div>
                      <span className="font-bold text-white">{slip.rider}</span>
                      <div className="mt-0.5 text-slate-400">
                        {slip.bank} • Ref: <span className="font-mono text-sky-400">{slip.ref}</span>
                      </div>
                      <div className="text-[11px] text-slate-500">{slip.date}</div>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="font-mono text-sm font-bold text-emerald-400">{slip.amount}</span>
                      <button className="rounded-lg bg-emerald-600 px-3 py-1 font-semibold text-white transition hover:bg-emerald-500">
                        Verify Deposit
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: BUSINESS / CORPORATE PORTAL */}
        {activeTab === 'business' && (
          <div className="flex h-full flex-col overflow-y-auto p-6">
            <h2 className="text-lg font-bold text-white">Corporate Merchant Services</h2>
            <p className="text-xs text-slate-400">Bulk delivery dispatch, instant quotation, and monthly billing</p>

            <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
              {/* Instant Delivery Quote Calculator */}
              <div className="glass-card rounded-2xl p-6">
                <h3 className="text-sm font-bold text-white">Instant Delivery Fare Calculator</h3>
                <form onSubmit={handleCalculateQuote} className="mt-4 space-y-4 text-xs">
                  <div>
                    <label className="text-slate-400">Pickup Address</label>
                    <input
                      type="text"
                      value={quoteInput.pickup_address}
                      onChange={(e) => setQuoteInput({ ...quoteInput, pickup_address: e.target.value })}
                      className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-900 p-2.5 text-white"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400">Dropoff Address</label>
                    <input
                      type="text"
                      value={quoteInput.dropoff_address}
                      onChange={(e) => setQuoteInput({ ...quoteInput, dropoff_address: e.target.value })}
                      className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-900 p-2.5 text-white"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-slate-400">Vehicle Type</label>
                      <select
                        value={quoteInput.vehicle_type}
                        onChange={(e) => setQuoteInput({ ...quoteInput, vehicle_type: e.target.value })}
                        className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-900 p-2.5 text-white"
                      >
                        <option value="BIKE">Motorcycle / Bike</option>
                        <option value="CAR">Car</option>
                        <option value="VAN">Delivery Van</option>
                        <option value="TRUCK">Mini Truck</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-slate-400">COD Goods Amount (PKR)</label>
                      <input
                        type="number"
                        value={quoteInput.cod_amount}
                        onChange={(e) => setQuoteInput({ ...quoteInput, cod_amount: e.target.value })}
                        className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-900 p-2.5 text-white"
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={isQuoting}
                    className="w-full rounded-xl bg-sky-600 py-2.5 text-xs font-bold text-white shadow-lg shadow-sky-600/20 transition hover:bg-sky-500"
                  >
                    {isQuoting ? 'Calculating...' : 'Get Binding Price Quote'}
                  </button>
                </form>

                {calculatedQuote && (
                  <div className="mt-5 rounded-xl border border-sky-500/30 bg-sky-950/20 p-4 text-xs">
                    <div className="flex items-center justify-between font-bold text-white">
                      <span>Total Guaranteed Fare:</span>
                      <span className="font-mono text-base text-sky-400">{calculatedQuote.total_price} PKR</span>
                    </div>
                    <div className="mt-2 grid grid-cols-2 gap-2 text-slate-400">
                      <div>Distance: {calculatedQuote.distance_km} km</div>
                      <div>Duration: ~{calculatedQuote.duration_minutes} mins</div>
                    </div>
                  </div>
                )}
              </div>

              {/* Bulk CSV Batch Import */}
              <div className="glass-card rounded-2xl p-6">
                <h3 className="text-sm font-bold text-white">Bulk Order Import (CSV)</h3>
                <p className="mt-1 text-xs text-slate-400">
                  Upload multiple deliveries at once with automated address geocoding & rider matching.
                </p>

                <div className="mt-4 flex h-44 flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-700 bg-slate-900/50 p-6 text-center text-xs">
                  <Upload className="mb-2 h-8 w-8 text-sky-400" />
                  <span className="font-semibold text-slate-200">Drag & drop CSV file or click to browse</span>
                  <span className="text-[11px] text-slate-500 mt-1">Columns: pickup_address, dropoff_address, recipient_name, phone, cod_amount</span>
                  <input
                    type="file"
                    accept=".csv"
                    onChange={(e) => setBulkFile(e.target.files[0])}
                    className="mt-3 text-xs text-slate-400"
                  />
                </div>

                {bulkFile && (
                  <button
                    onClick={() => {
                      setBulkProgress('Processing 45 rows... 100% complete.');
                    }}
                    className="mt-4 w-full rounded-xl bg-emerald-600 py-2.5 text-xs font-bold text-white transition hover:bg-emerald-500"
                  >
                    Upload & Dispatch Batch ({bulkFile.name})
                  </button>
                )}

                {bulkProgress && (
                  <div className="mt-3 rounded-lg bg-emerald-950/30 p-2.5 text-center text-xs text-emerald-400">
                    {bulkProgress}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 6: SURGE & TARIFFS */}
        {activeTab === 'surge' && (
          <div className="flex h-full flex-col overflow-y-auto p-6">
            <h2 className="text-lg font-bold text-white">Dynamic Surge Hexagons & Pricing Tariffs</h2>
            <p className="text-xs text-slate-400">Uber H3 spatial cells, automated surge multipliers, and vehicle base fares</p>

            <div className="mt-5 grid grid-cols-4 gap-4">
              {[
                { type: 'BIKE', base: '100.00', km: '25.00', min: '100.00' },
                { type: 'CAR', base: '200.00', km: '40.00', min: '200.00' },
                { type: 'VAN', base: '400.00', km: '60.00', min: '400.00' },
                { type: 'TRUCK', base: '800.00', km: '90.00', min: '800.00' },
              ].map((rule) => (
                <div key={rule.type} className="glass-card rounded-2xl p-5 text-xs">
                  <span className="font-bold text-sky-400">{rule.type}</span>
                  <div className="mt-3 space-y-1.5 text-slate-300">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Base Fare:</span>
                      <span className="font-bold text-white">{rule.base} PKR</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Per KM:</span>
                      <span className="font-bold text-white">{rule.km} PKR</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Minimum:</span>
                      <span className="font-bold text-white">{rule.min} PKR</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* ─── Manual Assignment Modal ─────────────────────────────────────── */}
      {assignModalOrder && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="glass-panel w-full max-w-md rounded-2xl p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-3">
              <h3 className="text-sm font-bold text-white">
                Assign Rider to Order <span className="font-mono text-sky-400">{assignModalOrder.order_number}</span>
              </h3>
              <button onClick={() => setAssignModalOrder(null)} className="text-slate-400 hover:text-white">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="mt-3 space-y-2 text-xs">
              <p className="text-slate-400">Select an online candidate rider:</p>
              {riders.map((r) => (
                <div
                  key={r.id}
                  onClick={() => handleAssignRider(r.id)}
                  className="flex cursor-pointer items-center justify-between rounded-xl bg-slate-900 p-3 transition hover:bg-slate-800"
                >
                  <div>
                    <span className="font-bold text-white">{r.name}</span>
                    <div className="text-[11px] text-slate-400">{r.vehicle_type} • ⭐ {r.rating}</div>
                  </div>
                  <span className="rounded bg-sky-500/20 px-2 py-1 font-semibold text-sky-300">
                    Select
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ─── Order Detail Modal ─────────────────────────────────────────── */}
      {selectedOrder && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="glass-panel w-full max-w-lg rounded-2xl p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div>
                <span className="font-mono text-xs font-bold text-sky-400">{selectedOrder.order_number}</span>
                <h3 className="text-base font-bold text-white">Order Lifecycle Details</h3>
              </div>
              <button onClick={() => setSelectedOrder(null)} className="text-slate-400 hover:text-white">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="mt-4 space-y-3 text-xs">
              <div className="flex justify-between rounded-lg bg-slate-900/60 p-3">
                <span className="text-slate-400">Status:</span>
                <span className="font-bold text-emerald-400">{selectedOrder.status}</span>
              </div>
              <div>
                <span className="text-slate-400">Pickup:</span>
                <p className="font-medium text-white">{selectedOrder.pickup_address}</p>
              </div>
              <div>
                <span className="text-slate-400">Dropoff:</span>
                <p className="font-medium text-white">{selectedOrder.dropoff_address}</p>
              </div>
              <div className="grid grid-cols-2 gap-4 border-t border-slate-800 pt-3">
                <div>
                  <span className="text-slate-400">Fare Amount:</span>
                  <p className="font-bold text-white">{selectedOrder.fare_amount} PKR</p>
                </div>
                <div>
                  <span className="text-slate-400">COD Goods Amount:</span>
                  <p className="font-bold text-cyan-400">{selectedOrder.cod_amount} PKR</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
