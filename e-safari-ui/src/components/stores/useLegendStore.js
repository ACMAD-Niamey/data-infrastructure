import { create } from "zustand/react";

export const useLegendStore = create((set) => ({
  legends: [],

  addLegend: (legend) =>
    set((state) => ({
      legends: [legend,...state.legends],
    })),

  clearLegends: () => set({ legends: [] }),

  removeLegendByTitle: (title) =>
    set((state) => ({
      legends: state.legends.filter((legend) => legend.props?.title !== title),
    })),
}));
