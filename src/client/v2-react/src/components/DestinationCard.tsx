import { motion } from 'framer-motion';
import { MapPin, Thermometer, ArrowRight } from 'lucide-react';
import type { Destination } from '@/types';

interface DestinationCardProps {
  destination: Destination;
  onViewHotels?: () => void;
  onViewFlights?: () => void;
  isActive?: boolean;
}

export function DestinationCard({ 
  destination, 
  onViewHotels, 
  onViewFlights,
  isActive = false 
}: DestinationCardProps) {
  return (
    <motion.div
      className="relative w-full h-full overflow-hidden rounded-3xl"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
    >
      {/* Background Image */}
      <div 
        className="absolute inset-0 bg-cover bg-center"
        style={{ backgroundImage: `url(${destination.image})` }}
      />
      
      {/* Gradient Overlay */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent" />
      
      {/* Content */}
      <div className="absolute inset-0 flex flex-col justify-end p-6">
        {/* Tags */}
        <div className="flex flex-wrap gap-2 mb-3">
          {destination.tags.map((tag, index) => (
            <motion.span
              key={tag}
              className="px-3 py-1 text-xs font-medium rounded-full bg-white/10 backdrop-blur-sm text-white/90"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 + index * 0.1 }}
            >
              {tag}
            </motion.span>
          ))}
        </div>

        {/* Title */}
        <motion.div
          className="mb-2"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-1">
            {destination.name}
          </h2>
          <p className="text-lg text-white/60 font-light">{destination.nameEn}</p>
        </motion.div>

        {/* Description */}
        <motion.p
          className="text-white/80 text-base mb-4 line-clamp-2"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          {destination.description}
        </motion.p>

        {/* Weather & Location */}
        <motion.div
          className="flex items-center gap-4 mb-4"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <div className="flex items-center gap-2 text-white/70">
            <MapPin className="w-4 h-4" />
            <span className="text-sm">{destination.name}</span>
          </div>
          <div className="flex items-center gap-2 text-white/70">
            <Thermometer className="w-4 h-4" />
            <span className="text-sm">{destination.weather.temp}°C {destination.weather.condition}</span>
          </div>
        </motion.div>

        {/* Action Buttons */}
        <motion.div
          className="flex gap-3"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
        >
          <button
            onClick={onViewHotels}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-white/10 backdrop-blur-sm hover:bg-white/20 transition-colors text-white text-sm font-medium"
          >
            查看酒店
            <ArrowRight className="w-4 h-4" />
          </button>
          <button
            onClick={onViewFlights}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl gradient-bg hover:opacity-90 transition-opacity text-[#1a1a1a] text-sm font-medium"
          >
            查看航班
            <ArrowRight className="w-4 h-4" />
          </button>
        </motion.div>
      </div>

      {/* Active Indicator */}
      {isActive && (
        <motion.div
          className="absolute top-4 right-4 w-3 h-3 rounded-full bg-[#d4a853]"
          animate={{ scale: [1, 1.2, 1] }}
          transition={{ duration: 1, repeat: Infinity }}
        />
      )}
    </motion.div>
  );
}

// Compact version for lists
export function DestinationCardCompact({ destination }: { destination: Destination }) {
  return (
    <motion.div
      className="relative flex-shrink-0 w-64 h-80 rounded-2xl overflow-hidden cursor-pointer group"
      whileHover={{ scale: 1.02 }}
      transition={{ duration: 0.3 }}
    >
      <div 
        className="absolute inset-0 bg-cover bg-center transition-transform duration-500 group-hover:scale-110"
        style={{ backgroundImage: `url(${destination.image})` }}
      />
      <div className="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent" />
      <div className="absolute bottom-0 left-0 right-0 p-4">
        <h3 className="text-xl font-semibold text-white mb-1">{destination.name}</h3>
        <p className="text-sm text-white/60">{destination.weather.temp}°C · {destination.weather.condition}</p>
      </div>
    </motion.div>
  );
}
