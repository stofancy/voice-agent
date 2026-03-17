import { motion } from 'framer-motion';
import { Star, MapPin, Wifi, Coffee, Car, Waves, Check } from 'lucide-react';
import type { Hotel } from '@/types';

interface HotelCardProps {
  hotel: Hotel;
  onSelect?: () => void;
}

const amenityIcons: Record<string, React.ReactNode> = {
  'WiFi': <Wifi className="w-3 h-3" />,
  '早餐': <Coffee className="w-3 h-3" />,
  '停车': <Car className="w-3 h-3" />,
  '泳池': <Waves className="w-3 h-3" />,
};

export function HotelCard({ hotel, onSelect }: HotelCardProps) {
  return (
    <motion.div
      className="flex-shrink-0 w-72 bg-[#2d2d2d]/80 backdrop-blur-sm rounded-2xl overflow-hidden cursor-pointer group"
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      whileHover={{ y: -4 }}
      transition={{ duration: 0.3 }}
      onClick={onSelect}
    >
      {/* Image */}
      <div className="relative h-40 overflow-hidden">
        <img
          src={hotel.image}
          alt={hotel.name}
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#2d2d2d] to-transparent opacity-60" />
        
        {/* Rating Badge */}
        <div className="absolute top-3 right-3 flex items-center gap-1 px-2 py-1 rounded-full bg-black/60 backdrop-blur-sm">
          <Star className="w-3 h-3 text-[#d4a853] fill-[#d4a853]" />
          <span className="text-xs font-medium text-white">{hotel.rating}</span>
        </div>

        {/* Stars */}
        <div className="absolute top-3 left-3 flex gap-0.5">
          {Array.from({ length: hotel.stars }).map((_, i) => (
            <Star key={i} className="w-3 h-3 text-[#d4a853] fill-[#d4a853]" />
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Name */}
        <h3 className="text-lg font-semibold text-white mb-1 line-clamp-1 group-hover:text-[#d4a853] transition-colors">
          {hotel.name}
        </h3>

        {/* Location */}
        <div className="flex items-center gap-1 text-white/50 mb-3">
          <MapPin className="w-3 h-3" />
          <span className="text-xs">{hotel.location}</span>
        </div>

        {/* Amenities */}
        <div className="flex flex-wrap gap-1.5 mb-4">
          {hotel.amenities.slice(0, 4).map((amenity) => (
            <span
              key={amenity}
              className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-white/5 text-white/60 text-xs"
            >
              {amenityIcons[amenity] || <Check className="w-3 h-3" />}
              {amenity}
            </span>
          ))}
        </div>

        {/* Price & Reviews */}
        <div className="flex items-end justify-between">
          <div>
            <span className="text-2xl font-bold gradient-text">{hotel.currency}{hotel.price}</span>
            <span className="text-xs text-white/40 ml-1">/晚</span>
          </div>
          <span className="text-xs text-white/40">{hotel.reviews} 条评价</span>
        </div>
      </div>
    </motion.div>
  );
}

// List version for vertical layout
export function HotelCardList({ hotel, onSelect }: HotelCardProps) {
  return (
    <motion.div
      className="flex gap-4 bg-[#2d2d2d]/60 backdrop-blur-sm rounded-xl p-3 cursor-pointer hover:bg-[#2d2d2d]/80 transition-colors"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      onClick={onSelect}
    >
      {/* Thumbnail */}
      <div className="w-24 h-24 rounded-lg overflow-hidden flex-shrink-0">
        <img
          src={hotel.image}
          alt={hotel.name}
          className="w-full h-full object-cover"
        />
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between mb-1">
          <h4 className="text-base font-medium text-white truncate pr-2">{hotel.name}</h4>
          <div className="flex items-center gap-1 flex-shrink-0">
            <Star className="w-3 h-3 text-[#d4a853] fill-[#d4a853]" />
            <span className="text-xs text-white">{hotel.rating}</span>
          </div>
        </div>

        <div className="flex items-center gap-1 text-white/50 mb-2">
          <MapPin className="w-3 h-3" />
          <span className="text-xs truncate">{hotel.location}</span>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex gap-0.5">
            {Array.from({ length: hotel.stars }).map((_, i) => (
              <Star key={i} className="w-3 h-3 text-[#d4a853] fill-[#d4a853]" />
            ))}
          </div>
          <span className="text-lg font-semibold gradient-text">{hotel.currency}{hotel.price}</span>
        </div>
      </div>
    </motion.div>
  );
}
