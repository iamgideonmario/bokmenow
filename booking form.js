// components/BookingForm.tsx
import React, { useState } from "react";
import axios from "../utils/api";
import { toast } from "sonner";

export default function BookingForm({ hostSlug, slot }: { hostSlug: string; slot: { start: string; end: string } }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await axios.post(`/api/v1/hosts/${hostSlug}/bookings`, {
        guest_name: name,
        guest_email: email,
        start_datetime: slot.start,
      });
      toast.success("Booking confirmed! Check your email (mock).");
      // Redirect to confirmation page
      window.location.href = `/${hostSlug}/confirm`;
    } catch (err) {
      toast.error("Failed to book. Slot may have been taken.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <input
        type="text"
        placeholder="Your name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        required
        className="w-full border p-2 rounded"
      />
      <input
        type="email"
        placeholder="Your email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
        className="w-full border p-2 rounded"
      />
      <button
        type="submit"
        disabled={submitting}
        className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
      >
        {submitting ? "Booking…" : "Book this slot"}
      </button>
    </form>
  );
}