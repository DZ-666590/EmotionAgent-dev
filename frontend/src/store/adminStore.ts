import { create } from 'zustand';

export interface InternalStateData {
  overall_state: string;
  risk_level: 'low' | 'medium' | 'high' | string;
  emotions: string[];
  intensity: number;
  symptoms: string[];
  stressors: string[];
}

interface AdminState {
  data: InternalStateData | null;
  updateData: (data: InternalStateData) => void;
}

export const useAdminStore = create<AdminState>((set) => ({
  data: null,
  updateData: (data) => set({ data }),
}));
