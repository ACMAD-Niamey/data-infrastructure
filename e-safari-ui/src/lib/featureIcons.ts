import {
  Thermometer, Leaf, Building2, Users, Globe, Layers, CalendarDays, BarChart3,
  Cloud, ShieldCheck, Handshake,
} from 'lucide-react';
import type { LucideProps } from 'lucide-react';
import type { ComponentType } from 'react';

export interface Feature {
  title: string;
  description: string;
  icon_name: string;
  layer_id?: string | null;
}

export type IconComponent = ComponentType<LucideProps>;

export const featureIconMap: Record<string, IconComponent> = {
  thermometer: Thermometer,
  leaf: Leaf,
  'building-2': Building2,
  users: Users,
  globe: Globe,
  layers: Layers,
  'calendar-days': CalendarDays,
  'bar-chart-3': BarChart3,
  cloud: Cloud,
  'shield-check': ShieldCheck,
  handshake: Handshake,
};

export const featureIconColors = ['#ea580c', '#16803d', '#ea580c', '#16803d', '#2563eb', '#16803d', '#ea580c', '#2563eb'];
export const featureIconBgs   = ['#fff7ed', '#f0fdf4', '#fff7ed', '#f0fdf4', '#eff6ff', '#f0fdf4', '#fff7ed', '#eff6ff'];
