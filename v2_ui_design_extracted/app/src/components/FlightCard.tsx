import { motion } from 'framer-motion';
import { Plane, Clock, ArrowRight } from 'lucide-react';
import type { Flight } from '@/types';

interface FlightCardProps {
  flight: Flight;
  onSelect?: () => void;
}

export function FlightCard({ flight, onSelect }: FlightCardProps) {
  return (
    <motion.div
      className="flex-shrink-0 w-80 bg-[#2d2d2d]/80 backdrop-blur-sm rounded-2xl p-5 cursor-pointer group"
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      whileHover={{ 
        y: -4,
        boxShadow: '0 8px 32px rgba(212, 168, 83, 0.15)'
      }}
      transition={{ duration: 0.3 }}
      onClick={onSelect}
    >
      {/* Header - Airline */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center">
            <span className="text-xs font-bold text-white">{flight.airline.slice(0, 2)}</span>
          </div>
          <div>
            <p className="text-sm font-medium text-white">{flight.airline}</p>
            <p className="text-xs text-white/50">{flight.flightNumber}</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold gradient-text">{flight.currency}{flight.price}</p>
          <p className="text-xs text-white/40">起</p>
        </div>
      </div>

      {/* Flight Route */}
      <div className="flex items-center justify-between mb-4">
        {/* Departure */}
        <div className="text-center">
          <p className="text-2xl font-bold text-white">{flight.departure.time}</p>
          <p className="text-sm text-white/60">{flight.departure.code}</p>
        </div>

        {/* Flight Path */}
        <div className="flex-1 px-4">
          <div className="flex items-center justify-center gap-2 mb-1">
            <div className="h-px flex-1 bg-gradient-to-r from-transparent to-white/30" />
            <Plane className="w-4 h-4 text-[#d4a853]" />
            <div className="h-px flex-1 bg-gradient-to-l from-transparent to-white/30" />
          </div>
          <div className="flex items-center justify-center gap-1 text-white/40">
            <Clock className="w-3 h-3" />
            <span className="text-xs">{flight.duration}</span>
          </div>
          {flight.stops > 0 && (
            <p className="text-center text-xs text-[#e07a5f] mt-0.5">
              经停{flight.stopCity}
            </p>
          )}
        </div>

        {/* Arrival */}
        <div className="text-center">
          <p className="text-2xl font-bold text-white">{flight.arrival.time}</p>
          <p className="text-sm text-white/60">{flight.arrival.code}</p>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-white/10">
        <div className="flex items-center gap-2 text-white/40">
          <span className="text-xs">{flight.departure.date}</span>
        </div>
        <motion.button
          className="flex items-center gap-1 text-sm text-[#d4a853] hover:text-[#e8c878] transition-colors"
          whileHover={{ x: 4 }}
        >
          选择
          <ArrowRight className="w-4 h-4" />
        </motion.button>
      </div>
    </motion.div>
  );
}

// Compact version
export function FlightCardCompact({ flight, onSelect }: FlightCardProps) {
  return (
    <motion.div
      className="flex items-center gap-4 bg-[#2d2d2d]/60 backdrop-blur-sm rounded-xl p-3 cursor-pointer hover:bg-[#2d2d2d]/80 transition-colors"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      onClick={onSelect}
    >
      {/* Airline Logo */}
      <div className="w-12 h-12 rounded-full bg-white/10 flex items-center justify-center flex-shrink-0">
        <span className="text-sm font-bold text-white">{flight.airline.slice(0, 2)}</span>
      </div>

      {/* Route Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm text-white/60">{flight.airline}</span>
          <span className="text-lg font-bold gradient-text">{flight.currency}{flight.price}</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            <span className="text-base font-medium text-white">{flight.departure.code}</span>
            <ArrowRight className="w-3 h-3 text-white/40" />
            <span className="text-base font-medium text-white">{flight.arrival.code}</span>
          </div>
          <span className="text-xs text-white/40">{flight.duration}</span>
        </div>
      </div>
    </motion.div>
  );
}
