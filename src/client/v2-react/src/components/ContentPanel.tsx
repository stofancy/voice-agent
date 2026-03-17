import { motion, AnimatePresence } from 'framer-motion';
import { X, ChevronLeft, ChevronRight, MapPin, Hotel, Plane } from 'lucide-react';
import type { Message } from '@/types';
import { DestinationCardCompact } from './DestinationCard';
import { HotelCard } from './HotelCard';
import { FlightCard } from './FlightCard';
import { useRef, useState } from 'react';
import { renderMarkdownSafe } from '@/lib/markdown';

interface ContentPanelProps {
  message: Message | null;
  onClose: () => void;
  visible: boolean;
}

type ContentTab = 'destinations' | 'hotels' | 'flights';

export function ContentPanel({ message, onClose, visible }: ContentPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeTab, setActiveTab] = useState<ContentTab>('destinations');

  if (!visible || !message) return null;

  const hasDestinations = message.destinations && message.destinations.length > 0;
  const hasHotels = message.hotels && message.hotels.length > 0;
  const hasFlights = message.flights && message.flights.length > 0;

  const scroll = (direction: 'left' | 'right') => {
    if (scrollRef.current) {
      const scrollAmount = 320;
      scrollRef.current.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth',
      });
    }
  };

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          className="absolute inset-x-0 bottom-0 z-20"
          initial={{ y: '100%' }}
          animate={{ y: 0 }}
          exit={{ y: '100%' }}
          transition={{ type: 'spring', damping: 25, stiffness: 200 }}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-gradient-to-t from-black via-black/80 to-transparent h-[120%] -top-[20%]" />

          {/* Content Container */}
          <div className="relative max-w-4xl mx-auto px-4 pb-8">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
              {/* Tabs */}
              <div className="flex gap-2">
                {hasDestinations && (
                  <TabButton
                    active={activeTab === 'destinations'}
                    onClick={() => setActiveTab('destinations')}
                    icon={<MapPin className="w-4 h-4" />}
                    label="目的地"
                  />
                )}
                {hasHotels && (
                  <TabButton
                    active={activeTab === 'hotels'}
                    onClick={() => setActiveTab('hotels')}
                    icon={<Hotel className="w-4 h-4" />}
                    label="酒店"
                  />
                )}
                {hasFlights && (
                  <TabButton
                    active={activeTab === 'flights'}
                    onClick={() => setActiveTab('flights')}
                    icon={<Plane className="w-4 h-4" />}
                    label="航班"
                  />
                )}
              </div>

              {/* Close Button */}
              <motion.button
                onClick={onClose}
                className="p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
              >
                <X className="w-5 h-5 text-white/70" />
              </motion.button>
            </div>

            {/* Scroll Controls */}
            {activeTab !== 'destinations' && (
              <>
                <button
                  onClick={() => scroll('left')}
                  className="absolute left-0 top-1/2 -translate-y-1/2 z-10 p-2 rounded-full bg-black/60 text-white/70 hover:text-white transition-colors"
                >
                  <ChevronLeft className="w-6 h-6" />
                </button>
                <button
                  onClick={() => scroll('right')}
                  className="absolute right-0 top-1/2 -translate-y-1/2 z-10 p-2 rounded-full bg-black/60 text-white/70 hover:text-white transition-colors"
                >
                  <ChevronRight className="w-6 h-6" />
                </button>
              </>
            )}

            {/* Content */}
            <div
              ref={scrollRef}
              className={`
                flex gap-4 overflow-x-auto hide-scrollbar pb-2
                ${activeTab === 'destinations' ? 'snap-x snap-mandatory' : ''}
              `}
            >
              <AnimatePresence mode="wait">
                {activeTab === 'destinations' && hasDestinations && (
                  <motion.div
                    key="destinations"
                    className="flex gap-4"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                  >
                    {message.destinations!.map((dest) => (
                      <div key={dest.id} className="snap-center">
                        <DestinationCardCompact destination={dest} />
                      </div>
                    ))}
                  </motion.div>
                )}

                {activeTab === 'hotels' && hasHotels && (
                  <motion.div
                    key="hotels"
                    className="flex gap-4"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                  >
                    {message.hotels!.map((hotel) => (
                      <HotelCard key={hotel.id} hotel={hotel} />
                    ))}
                  </motion.div>
                )}

                {activeTab === 'flights' && hasFlights && (
                  <motion.div
                    key="flights"
                    className="flex gap-4"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                  >
                    {message.flights!.map((flight) => (
                      <FlightCard key={flight.id} flight={flight} />
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Message Text */}
            {message.content && (
              <motion.div
                className="mt-4 p-4 rounded-xl bg-white/5 backdrop-blur-sm"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <div 
                  className="text-white/80 text-sm leading-relaxed markdown-content"
                  dangerouslySetInnerHTML={{ __html: renderMarkdownSafe(message.content) }}
                />
              </motion.div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function TabButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <motion.button
      onClick={onClick}
      className={`
        flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all
        ${active 
          ? 'gradient-bg text-[#1a1a1a]' 
          : 'bg-white/10 text-white/70 hover:bg-white/20 hover:text-white'
        }
      `}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
      {icon}
      {label}
    </motion.button>
  );
}
