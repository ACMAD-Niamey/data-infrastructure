export interface PointDataReading {
  id: string;
  name: string;
  location: [number, number];
  sunTemp: number;
  shadeTemp: number;
  date: string;
  collector: string;
}

export const pointData: PointDataReading[] = [
  {
    id: '1',
    name: 'Market District',
    location: [13.5127, 2.1128],
    sunTemp: 45.2,
    shadeTemp: 38.5,
    date: '2024-11-15',
    collector: 'Community Team A'
  },
  {
    id: '2',
    name: 'School Compound',
    location: [13.5200, 2.1050],
    sunTemp: 43.8,
    shadeTemp: 36.2,
    date: '2024-11-15',
    collector: 'Youth Group B'
  },
  {
    id: '3',
    name: 'Residential Area',
    location: [13.5050, 2.1200],
    sunTemp: 46.1,
    shadeTemp: 39.0,
    date: '2024-11-14',
    collector: 'Community Team A'
  },
  {
    id: '4',
    name: 'Park Zone',
    location: [13.5150, 2.1100],
    sunTemp: 42.3,
    shadeTemp: 34.8,
    date: '2024-11-14',
    collector: 'Youth Group C'
  },
  {
    id: '5',
    name: 'Informal Settlement',
    location: [13.5080, 2.1180],
    sunTemp: 44.9,
    shadeTemp: 37.6,
    date: '2024-11-13',
    collector: 'Community Team B'
  },
  {
    id: '6',
    name: 'Bus Station',
    location: [13.5180, 2.1180],
    sunTemp: 45.5,
    shadeTemp: 38.9,
    date: '2024-11-13',
    collector: 'Youth Group A'
  },
  {
    id: '7',
    name: 'Community Center',
    location: [13.5220, 2.1080],
    sunTemp: 43.2,
    shadeTemp: 35.7,
    date: '2024-11-12',
    collector: 'Community Team C'
  },
  {
    id: '8',
    name: 'Industrial Area',
    location: [13.5100, 2.1050],
    sunTemp: 46.8,
    shadeTemp: 40.1,
    date: '2024-11-12',
    collector: 'Youth Group B'
  }
];
