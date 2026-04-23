def generate_slots(host, start_date, end_date):
    slots = []
    # Iterate each day in range
    for single_date in date_range(start_date, end_date):
        day_of_week = single_date.weekday()  # Monday=0
        # Find matching availability patterns
        patterns = db.session.query(Availability).filter_by(host_id=host.id, day_of_week=day_of_week).all()
        for p in patterns:
            # Convert local times to UTC
            start_local = datetime.combine(single_date, p.start_time)
            end_local   = datetime.combine(single_date, p.end_time)
            start_utc = tz.localize(start_local).astimezone(pytz.utc)
            end_utc   = tz.localize(end_local).astimezone(pytz.utc)

            # Split into slots of duration
            slot_start = start_utc
            while slot_start + timedelta(minutes=p.slot_duration_minutes) <= end_utc:
                slot_end = slot_start + timedelta(minutes=p.slot_duration_minutes)
                slots.append({
                    "start": slot_start.isoformat(),
                    "end":   slot_end.isoformat()
                })
                slot_start = slot_end
    return slots