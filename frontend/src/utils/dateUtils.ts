// src/utils/dateUtils.ts
import { format, formatDistanceToNow, formatRelative, isToday, isTomorrow, isYesterday, differenceInDays, startOfWeek, endOfWeek, addDays, parseISO, isValid } from 'date-fns';

// Format dates with different styles
export const DateFormats = {
  SHORT: 'MMM d, yyyy',
  LONG: 'MMMM d, yyyy',
  FULL: 'EEEE, MMMM d, yyyy',
  TIME: 'h:mm a',
  SHORT_TIME: 'h:mm a',
  FULL_TIME: 'EEEE, MMMM d, yyyy h:mm a',
  DATE_TIME: 'MMM d, yyyy h:mm a',
  WEEK_START: 'MMM d',
  WEEK_RANGE: 'MMM d, yyyy',
  ISO: 'yyyy-MM-dd',
  SLASH: 'MM/dd/yyyy',
  DOT: 'dd.MM.yyyy',
};

// Main date formatting function
export const formatDate = (date: string | Date | null | undefined, formatStr: string = DateFormats.SHORT): string => {
  if (!date) return 'N/A';
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    if (!isValid(dateObj)) return 'Invalid Date';
    return format(dateObj, formatStr);
  } catch {
    return 'Invalid Date';
  }
};

// Get relative time (e.g., "2 days ago")
export const getRelativeTime = (date: string | Date | null | undefined): string => {
  if (!date) return 'N/A';
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    if (!isValid(dateObj)) return 'Invalid Date';
    return formatDistanceToNow(dateObj, { addSuffix: true });
  } catch {
    return 'Invalid Date';
  }
};

// Get relative time with custom formats
export const getSmartDate = (date: string | Date | null | undefined): string => {
  if (!date) return 'N/A';
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    if (!isValid(dateObj)) return 'Invalid Date';
    
    if (isToday(dateObj)) return 'Today';
    if (isTomorrow(dateObj)) return 'Tomorrow';
    if (isYesterday(dateObj)) return 'Yesterday';
    
    const daysDiff = differenceInDays(new Date(), dateObj);
    if (daysDiff < 7) return formatRelative(dateObj, new Date());
    return format(dateObj, DateFormats.SHORT);
  } catch {
    return 'Invalid Date';
  }
};

// Get week range
export const getWeekRange = (weekStart: string | Date): { start: Date; end: Date; startStr: string; endStr: string } => {
  try {
    const start = typeof weekStart === 'string' ? parseISO(weekStart) : weekStart;
    const end = endOfWeek(start, { weekStartsOn: 1 });
    return {
      start,
      end,
      startStr: format(start, DateFormats.SHORT),
      endStr: format(end, DateFormats.SHORT),
    };
  } catch {
    const now = new Date();
    const start = startOfWeek(now, { weekStartsOn: 1 });
    const end = endOfWeek(now, { weekStartsOn: 1 });
    return {
      start,
      end,
      startStr: format(start, DateFormats.SHORT),
      endStr: format(end, DateFormats.SHORT),
    };
  }
};

// Get day name
export const getDayName = (date: string | Date): string => {
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    return format(dateObj, 'EEEE');
  } catch {
    return 'Unknown';
  }
};

// Get short day name
export const getShortDayName = (date: string | Date): string => {
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    return format(dateObj, 'EEE');
  } catch {
    return 'Unknown';
  }
};

// Check if date is in current week
export const isInCurrentWeek = (date: string | Date): boolean => {
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    const now = new Date();
    const weekStart = startOfWeek(now, { weekStartsOn: 1 });
    const weekEnd = endOfWeek(now, { weekStartsOn: 1 });
    return dateObj >= weekStart && dateObj <= weekEnd;
  } catch {
    return false;
  }
};

// Get week number
export const getWeekNumber = (date: string | Date): number => {
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    return parseInt(format(dateObj, 'w'));
  } catch {
    return 0;
  }
};

// Format for input
export const formatDateForInput = (date: string | Date | null | undefined): string => {
  if (!date) return '';
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    if (!isValid(dateObj)) return '';
    return format(dateObj, 'yyyy-MM-dd');
  } catch {
    return '';
  }
};

// Get date from input
export const parseDateFromInput = (dateStr: string): Date | null => {
  if (!dateStr) return null;
  try {
    const date = parseISO(dateStr);
    return isValid(date) ? date : null;
  } catch {
    return null;
  }
};