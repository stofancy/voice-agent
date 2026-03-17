export interface Destination {
  id: string;
  name: string;
  nameEn: string;
  description: string;
  image: string;
  weather: {
    temp: number;
    condition: string;
    icon: string;
  };
  tags: string[];
}

export interface Hotel {
  id: string;
  name: string;
  location: string;
  image: string;
  price: number;
  currency: string;
  rating: number;
  reviews: number;
  stars: number;
  amenities: string[];
}

export interface Flight {
  id: string;
  airline: string;
  airlineLogo: string;
  flightNumber: string;
  departure: {
    airport: string;
    code: string;
    time: string;
    date: string;
  };
  arrival: {
    airport: string;
    code: string;
    time: string;
    date: string;
  };
  price: number;
  currency: string;
  duration: string;
  stops: number;
  stopCity?: string;
}

export interface TripDay {
  day: number;
  date: string;
  activities: Activity[];
}

export interface Activity {
  id: string;
  time: string;
  title: string;
  description: string;
  type: 'flight' | 'hotel' | 'sightseeing' | 'dining' | 'transport';
  icon: string;
}

export type VoiceState = 'idle' | 'listening' | 'processing' | 'speaking';

export interface Message {
  id: string;
  type: 'user' | 'agent';
  content: string;
  timestamp: number;
  destinations?: Destination[];
  hotels?: Hotel[];
  flights?: Flight[];
}
