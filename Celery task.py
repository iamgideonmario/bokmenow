@app.post("/api/v1/hosts/{host_id}/bookings")
def create_booking(host_id: UUID, booking: BookingCreate, db: Session = Depends(get_db)):
    # ... validation & insertion ...
    send_confirmation_email.delay(booking.id)  # async
    return booking