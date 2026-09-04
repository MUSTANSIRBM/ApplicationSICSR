// src/components/ui/DatePicker.tsx
import { useState, useRef, useEffect } from 'react';
import { Calendar, ChevronLeft, ChevronRight } from 'lucide-react';
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isToday, isSameDay, startOfWeek, endOfWeek, addMonths, subMonths, isWeekend } from 'date-fns';
import { clsx } from 'clsx';

interface DatePickerProps {
  value: string;
  onChange: (date: string) => void;
  placeholder?: string;
  className?: string;
  label?: string;
}

export function DatePicker({ value, onChange, placeholder = 'Select date...', className = '', label }: DatePickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const selectedDate = value ? new Date(value) : null;

  const days = eachDayOfInterval({
    start: startOfWeek(currentMonth, { weekStartsOn: 1 }),
    end: endOfWeek(currentMonth, { weekStartsOn: 1 }),
  });

  const handleDateSelect = (date: Date) => {
    onChange(format(date, 'yyyy-MM-dd'));
    setIsOpen(false);
  };

  const goToPreviousMonth = () => setCurrentMonth(subMonths(currentMonth, 1));
  const goToNextMonth = () => setCurrentMonth(addMonths(currentMonth, 1));

  return (
    <div ref={wrapperRef} className="relative">
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      )}
      <div className="relative">
        <input
          type="text"
          value={selectedDate ? format(selectedDate, 'MMM d, yyyy') : ''}
          placeholder={placeholder}
          className={`w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all cursor-pointer ${className}`}
          onFocus={() => setIsOpen(true)}
          readOnly
        />
        <Calendar className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
      </div>

      {isOpen && (
        <div className="absolute top-full left-0 mt-1 bg-white rounded-xl shadow-2xl border border-gray-200 p-3 z-50 min-w-[280px] animate-fade-in">
          <div className="flex items-center justify-between mb-2">
            <button onClick={goToPreviousMonth} className="p-1 rounded-lg hover:bg-gray-100 transition-colors">
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-sm font-medium text-gray-700">
              {format(currentMonth, 'MMMM yyyy')}
            </span>
            <button onClick={goToNextMonth} className="p-1 rounded-lg hover:bg-gray-100 transition-colors">
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          <div className="grid grid-cols-7 gap-0.5">
            {['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'].map((day) => (
              <div key={day} className="p-1 text-center text-xs font-medium text-gray-400">
                {day}
              </div>
            ))}
            {days.map((day) => {
              const isSelected = selectedDate ? isSameDay(day, selectedDate) : false;
              const isTodayDate = isToday(day);
              const isWeekendDate = isWeekend(day);
              
              return (
                <button
                  key={day.toISOString()}
                  onClick={() => handleDateSelect(day)}
                  className={clsx(
                    'p-1.5 text-center text-xs rounded-lg transition-colors',
                    isSelected && 'bg-blue-100 text-blue-700 font-semibold ring-2 ring-blue-500',
                    isTodayDate && !isSelected && 'bg-blue-500 text-white hover:bg-blue-600',
                    !isTodayDate && !isSelected && 'hover:bg-blue-50 hover:text-blue-600',
                    isWeekendDate && !isSelected && !isTodayDate && 'text-red-400',
                    day.getMonth() !== currentMonth.getMonth() && 'text-gray-300 hover:bg-transparent'
                  )}
                >
                  {format(day, 'd')}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}