import { create } from 'zustand';

interface UIState {
  isVoiceMode: boolean;
  toggleVoiceMode: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  isVoiceMode: false,
  toggleVoiceMode: () => set((state) => ({ isVoiceMode: !state.isVoiceMode })),
}));
