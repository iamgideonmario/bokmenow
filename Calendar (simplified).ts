// components/Calendar.tsx
import React, { useEffect, useState } from "react";
import { format, parseISO, startOfMonth, endOfMonth, eachDayOfInterval } from "date-fns";
import { useRouter } from "next/router";
import axios from "../utils/api";

interface Slot {
  start: string;
  end: string;
}

export default function Calendar({ hostSlug }: { hostSlug: string }) {
  const [slots, setSlots] = useState<Slot[]>([]);
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const router = useRouter();

  useEffect(() => {
    const fetchSlots = async () => {
      const start = format(new Date(), "yyyy-MM-dd");
      const end = format(new Date(new Date().setMonth(new Date().getMonth() + 1)), "yyyy-MM-dd");
      const { data } = await axios.get(`/api/v1/hosts/${hostSlug}/available-slots`, {
        params: { start, end },
      });
      setSlots(data.slots);
    };
    fetchSlots();
  }, [hostSlug]);

  const daysInMonth = eachDayOfInterval({
    start: startOfMonth(new Date()),
    end: endOfMonth(new Date()),
  });

  const slotsForDate = (date: Date) =>
    slots.filter((s) => format(parseISO(s.start), "yyyy-MM-dd") === format(date, "yyyy-MM-dd"));

  return (
    <div className="grid grid-cols-7 gap-2">
      {daysInMonth.map((day) => {
        const daySlots = slotsForDate(day);
        return (
          <div
            key={day.toISOString()}
            className="p-2 border rounded cursor-pointer hover:bg-gray-100"
            onClick={() => setSelectedDate(day)}
          >
            <div className="font-semibold">{format(day, "d")}</div>
            {daySlots.length > 0 && (
              <div className="mt-1 text-sm text-blue-600">{daySlots.length} slot(s)</div>
            )}
          </div>
        );
      })}
    </div>
  );
}