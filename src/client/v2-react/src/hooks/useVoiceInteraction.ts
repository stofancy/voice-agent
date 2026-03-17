import { useState, useCallback, useRef, useEffect } from 'react';
import type { VoiceState, Message, Destination, Hotel, Flight } from '@/types';

// Mock data for destinations
const mockDestinations: Destination[] = [
  {
    id: '1',
    name: '巴黎',
    nameEn: 'Paris',
    description: '浪漫之都，艺术与时尚的完美融合。埃菲尔铁塔、卢浮宫、香榭丽舍大街等待您的探索。',
    image: 'https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=800&q=80',
    weather: { temp: 18, condition: '晴朗', icon: 'sun' },
    tags: ['浪漫', '艺术', '美食'],
  },
  {
    id: '2',
    name: '东京',
    nameEn: 'Tokyo',
    description: '传统与现代交织的大都市。浅草寺、涩谷十字路口、秋叶原，体验独特的日本文化。',
    image: 'https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=800&q=80',
    weather: { temp: 22, condition: '多云', icon: 'cloud' },
    tags: ['现代', '美食', '购物'],
  },
  {
    id: '3',
    name: '马尔代夫',
    nameEn: 'Maldives',
    description: '印度洋上的珍珠，一岛一酒店的奢华体验。碧蓝海水、白色沙滩、水上别墅。',
    image: 'https://images.unsplash.com/photo-1514282401047-d79a71a590e8?w=800&q=80',
    weather: { temp: 29, condition: '晴朗', icon: 'sun' },
    tags: ['海岛', '度假', '潜水'],
  },
  {
    id: '4',
    name: '冰岛',
    nameEn: 'Iceland',
    description: '冰与火之国，极光、冰川、温泉、火山，大自然的鬼斧神工。',
    image: 'https://images.unsplash.com/photo-1476610182048-b716b8518aae?w=800&q=80',
    weather: { temp: 5, condition: '阴天', icon: 'cloud' },
    tags: ['极光', '自然', '探险'],
  },
];

// Mock data for hotels
const mockHotels: Hotel[] = [
  {
    id: '1',
    name: '巴黎丽兹酒店',
    location: '巴黎，第一区',
    image: 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&q=80',
    price: 1280,
    currency: '€',
    rating: 4.9,
    reviews: 2847,
    stars: 5,
    amenities: ['WiFi', '泳池', 'SPA', '早餐'],
  },
  {
    id: '2',
    name: '东京安缦',
    location: '东京，千代田区',
    image: 'https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600&q=80',
    price: 950,
    currency: '¥',
    rating: 4.8,
    reviews: 1523,
    stars: 5,
    amenities: ['WiFi', '温泉', '早餐', '停车'],
  },
  {
    id: '3',
    name: '马尔代夫四季',
    location: '芭环礁',
    image: 'https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=600&q=80',
    price: 2100,
    currency: '$',
    rating: 4.9,
    reviews: 987,
    stars: 5,
    amenities: ['WiFi', '泳池', '潜水', 'SPA'],
  },
  {
    id: '4',
    name: '冰岛离子酒店',
    location: '雷克雅未克',
    image: 'https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=600&q=80',
    price: 380,
    currency: '€',
    rating: 4.6,
    reviews: 2156,
    stars: 4,
    amenities: ['WiFi', '极光观测', '温泉', '早餐'],
  },
];

// Mock data for flights
const mockFlights: Flight[] = [
  {
    id: '1',
    airline: '法国航空',
    airlineLogo: 'AF',
    flightNumber: 'AF123',
    departure: { airport: '北京首都', code: 'PEK', time: '23:50', date: '12月15日' },
    arrival: { airport: '巴黎戴高乐', code: 'CDG', time: '05:30', date: '12月16日' },
    price: 6800,
    currency: '¥',
    duration: '11小时40分',
    stops: 0,
  },
  {
    id: '2',
    airline: '日本航空',
    airlineLogo: 'JL',
    flightNumber: 'JL022',
    departure: { airport: '北京首都', code: 'PEK', time: '16:20', date: '12月15日' },
    arrival: { airport: '东京羽田', code: 'HND', time: '20:50', date: '12月15日' },
    price: 4200,
    currency: '¥',
    duration: '3小时30分',
    stops: 0,
  },
  {
    id: '3',
    airline: '新加坡航空',
    airlineLogo: 'SQ',
    flightNumber: 'SQ803',
    departure: { airport: '北京首都', code: 'PEK', time: '16:35', date: '12月15日' },
    arrival: { airport: '马累', code: 'MLE', time: '00:45', date: '12月16日' },
    price: 8900,
    currency: '¥',
    duration: '8小时10分',
    stops: 1,
    stopCity: '新加坡',
  },
];

// Speech Recognition types
interface SpeechRecognitionEvent extends Event {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
}

interface SpeechRecognitionResultList {
  length: number;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
  isFinal: boolean;
  [index: number]: { transcript: string };
}

interface SpeechRecognitionInterface extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
}

declare global {
  interface Window {
    SpeechRecognition: new () => SpeechRecognitionInterface;
    webkitSpeechRecognition: new () => SpeechRecognitionInterface;
  }
}

export function useVoiceInteraction() {
  const [voiceState, setVoiceState] = useState<VoiceState>('idle');
  const [transcript, setTranscript] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentMessage, setCurrentMessage] = useState<Message | null>(null);
  const [showContent, setShowContent] = useState(false);
  const [subtitleEnabled, setSubtitleEnabled] = useState(true);
  
  const recognitionRef = useRef<SpeechRecognitionInterface | null>(null);
  const synthesisRef = useRef<SpeechSynthesis | null>(null);

  // Initialize speech recognition
  useEffect(() => {
    if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = true;
      recognitionRef.current.interimResults = true;
      recognitionRef.current.lang = 'zh-CN';

      recognitionRef.current.onresult = (event: SpeechRecognitionEvent) => {
        let finalTranscript = '';
        let interimTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript;
          } else {
            interimTranscript += transcript;
          }
        }

        if (finalTranscript) {
          setTranscript((prev) => prev + finalTranscript);
        }
      };

      recognitionRef.current.onerror = (event: SpeechRecognitionErrorEvent) => {
        console.error('Speech recognition error:', event.error);
        setVoiceState('idle');
      };

      recognitionRef.current.onend = () => {
        if (voiceState === 'listening') {
          setVoiceState('idle');
        }
      };
    }

    // Initialize speech synthesis
    if ('speechSynthesis' in window) {
      synthesisRef.current = window.speechSynthesis;
    }

    return () => {
      recognitionRef.current?.stop();
    };
  }, []);

  const startListening = useCallback(() => {
    if (recognitionRef.current && voiceState === 'idle') {
      setTranscript('');
      setVoiceState('listening');
      recognitionRef.current.start();
    }
  }, [voiceState]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current && voiceState === 'listening') {
      recognitionRef.current.stop();
      setVoiceState('processing');
      
      // Simulate agent response
      setTimeout(() => {
        handleAgentResponse(transcript);
      }, 1500);
    }
  }, [voiceState, transcript]);

  const handleAgentResponse = useCallback((userInput: string) => {
    // Simulate AI response based on user input
    let response: Message;
    
    const lowerInput = userInput.toLowerCase();
    
    if (lowerInput.includes('巴黎') || lowerInput.includes('法国')) {
      response = {
        id: Date.now().toString(),
        type: 'agent',
        content: '我为您找到了巴黎的精选行程！巴黎是浪漫之都，这里有世界顶级的艺术博物馆、米其林餐厅和时尚街区。我为您推荐了几家豪华酒店和直飞航班。',
        timestamp: Date.now(),
        destinations: [mockDestinations[0]],
        hotels: [mockHotels[0]],
        flights: [mockFlights[0]],
      };
    } else if (lowerInput.includes('东京') || lowerInput.includes('日本')) {
      response = {
        id: Date.now().toString(),
        type: 'agent',
        content: '东京是个绝佳的选择！这座现代与传统完美融合的城市有着无穷的魅力。从浅草寺到涩谷，从寿司到拉面，每一刻都是新体验。',
        timestamp: Date.now(),
        destinations: [mockDestinations[1]],
        hotels: [mockHotels[1]],
        flights: [mockFlights[1]],
      };
    } else if (lowerInput.includes('马尔代夫') || lowerInput.includes('海岛')) {
      response = {
        id: Date.now().toString(),
        type: 'agent',
        content: '马尔代夫是度假的天堂！一岛一酒店的私密体验，碧蓝的海水、白色的沙滩，还有令人惊叹的水上别墅。这是放松身心的完美去处。',
        timestamp: Date.now(),
        destinations: [mockDestinations[2]],
        hotels: [mockHotels[2]],
        flights: [mockFlights[2]],
      };
    } else if (lowerInput.includes('冰岛') || lowerInput.includes('极光')) {
      response = {
        id: Date.now().toString(),
        type: 'agent',
        content: '冰岛是探险者的梦想之地！在这里您可以追逐北极光、探索冰川洞穴、浸泡在蓝湖温泉中。这是大自然最壮观的展示。',
        timestamp: Date.now(),
        destinations: [mockDestinations[3]],
        hotels: [mockHotels[3]],
        flights: [mockFlights[0]],
      };
    } else {
      response = {
        id: Date.now().toString(),
        type: 'agent',
        content: '很高兴为您规划旅行！根据您的需求，我为您推荐几个热门目的地。您可以告诉我更具体的偏好，比如喜欢海岛、城市还是自然风光？',
        timestamp: Date.now(),
        destinations: mockDestinations,
        hotels: mockHotels,
        flights: mockFlights,
      };
    }

    setCurrentMessage(response);
    setMessages((prev) => [...prev, response]);
    setVoiceState('speaking');
    setShowContent(true);

    // Speak the response
    speakResponse(response.content);
  }, []);

  const speakResponse = useCallback((text: string) => {
    if (synthesisRef.current) {
      // Cancel any ongoing speech
      synthesisRef.current.cancel();

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'zh-CN';
      utterance.rate = 1;
      utterance.pitch = 1;

      utterance.onend = () => {
        setVoiceState('idle');
      };

      synthesisRef.current.speak(utterance);
    } else {
      setTimeout(() => setVoiceState('idle'), 3000);
    }
  }, []);

  const toggleSubtitle = useCallback(() => {
    setSubtitleEnabled((prev) => !prev);
  }, []);

  const closeContent = useCallback(() => {
    setShowContent(false);
  }, []);

  return {
    voiceState,
    transcript,
    messages,
    currentMessage,
    showContent,
    subtitleEnabled,
    startListening,
    stopListening,
    toggleSubtitle,
    closeContent,
  };
}
