import React, { useState } from 'react';

const CalComBooking = () => {
  const API_KEY = 'cal_live_755d4731d98914c78688a13df6bccf0d';
  const EVENT_TYPE_ID = '1715734';
  
  const [selectedDate, setSelectedDate] = useState('');
  const [patientName, setPatientName] = useState('');
  const [patientEmail, setPatientEmail] = useState('');
  const [notes, setNotes] = useState('');
  const [availableSlots, setAvailableSlots] = useState([]);
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchAvailableSlots = async () => {
    if (!patientName || !patientEmail || !selectedDate) {
      setError('Please fill in all required fields');
      return;
    }

    setLoading(true);
    setError('');
    const selecteddate = new Date(selectedDate);
    selecteddate.setDate(selecteddate.getDate()+1)
    console.log(selectedDate,selecteddate)
    try {
      const params = new URLSearchParams({
        apiKey: API_KEY,
        eventTypeId: EVENT_TYPE_ID,
        startTime: selectedDate,
        endTime: selecteddate,
        username: 'monish-kumar-rcpks6'
      });

      const response = await fetch(`https://api.cal.com/v1/slots?${params}`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch available slots');
      }

      const data = await response.json();
      const formattedSlots = Object.entries(data.slots || {}).flatMap(([date, slots]) =>
        slots.map(slot => {
          const startTime = new Date(slot.time);
          const endTime = new Date(startTime.getTime() + 30 * 60000);
          return {
            startTime,
            endTime,
            displayTime: startTime.toLocaleTimeString('en-US', {
              hour: 'numeric',
              minute: '2-digit',
              hour12: true
            })
          };
        })
      );

      setAvailableSlots(formattedSlots);
    } catch (error) {
      setError(`Error fetching slots: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const bookAppointment = async () => {
    if (!selectedSlot) {
      setError('Please select a time slot');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch('https://api.cal.com/v2/bookings', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${API_KEY}`,
          'Content-Type': 'application/json',
          'cal-api-version': '2024-08-13'
        },
        body: JSON.stringify({
          "start": selectedSlot.startTime.toISOString(),  
            "eventTypeId": 1715734,  
              "attendee": {
              "name":patientName, 
        "email": patientEmail,  
        "timeZone": "Asia/Kolkata",  
        "language": "en"  
    },
    "guests": [
        "springboardmentor539@gmail.com" 
    ]
        })
      });

      if (!response.ok) {
        throw new Error('Failed to book appointment');
      }

      // Clear form after successful booking
      setPatientName('');
      setPatientEmail('');
      setNotes('');
      setSelectedDate('');
      setSelectedSlot(null);
      setAvailableSlots([]);
      
      alert('Appointment booked successfully!');
    } catch (error) {
      setError(`Error booking appointment: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const containerStyle = {
    maxWidth: '600px',
    margin: '0 auto',
    padding: '20px',
    fontFamily: 'Arial, sans-serif'
  };

  const formGroupStyle = {
    marginBottom: '15px'
  };

  const labelStyle = {
    display: 'block',
    marginBottom: '5px',
    fontWeight: 'bold'
  };

  const inputStyle = {
    width: '100%',
    padding: '8px',
    border: '1px solid #ccc',
    borderRadius: '4px',
    marginBottom: '10px'
  };

  const buttonStyle = {
    backgroundColor: '#007bff',
    color: 'white',
    padding: '10px 15px',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    width: '100%'
  };

  const disabledButtonStyle = {
    ...buttonStyle,
    backgroundColor: '#ccc',
    cursor: 'not-allowed'
  };

  const errorStyle = {
    color: 'red',
    marginBottom: '10px'
  };

  const slotButtonStyle = {
    padding: '8px',
    margin: '5px',
    border: '1px solid #007bff',
    borderRadius: '4px',
    cursor: 'pointer',
    backgroundColor: 'white',
    color: '#007bff'
  };

  const selectedSlotStyle = {
    ...slotButtonStyle,
    backgroundColor: '#007bff',
    color: 'white'
  };

  const slotsContainerStyle = {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))',
    gap: '10px',
    marginTop: '10px'
  };

  return (
    <div style={containerStyle}>
      <h1 style={{ textAlign: 'center', marginBottom: '20px' }}>📅 Schedule Appointment</h1>
      
      <div style={formGroupStyle}>
        <label style={labelStyle}>Patient Name</label>
        <input
          type="text"
          value={patientName}
          onChange={(e) => setPatientName(e.target.value)}
          placeholder="Enter patient name"
          style={inputStyle}
        />
      </div>

      <div style={formGroupStyle}>
        <label style={labelStyle}>Patient Email</label>
        <input
          type="email"
          value={patientEmail}
          onChange={(e) => setPatientEmail(e.target.value)}
          placeholder="Enter patient email"
          style={inputStyle}
        />
      </div>

      <div style={formGroupStyle}>
        <label style={labelStyle}>Select Date</label>
        <input
          type="date"
          value={selectedDate}
          onChange={(e) => setSelectedDate(e.target.value)}
          style={inputStyle}
        />
      </div>

      <div style={formGroupStyle}>
        <label style={labelStyle}>Additional Notes</label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Add any additional notes here..."
          style={{ ...inputStyle, height: '100px', resize: 'vertical' }}
        />
      </div>

      <button 
        onClick={fetchAvailableSlots}
        disabled={loading}
        
      >
        {loading ? 'Checking availability...' : 'Check Available Slots'}
      </button>

      {error && (
        <div style={errorStyle}>{error}</div>
      )}

      {availableSlots.length > 0 && (
        <div style={{ marginTop: '20px' }}>
          <label style={labelStyle}>Available Time Slots</label>
          <div style={slotsContainerStyle}>
            {availableSlots.map((slot, index) => (
              <button id = "slot"
                key={index}
                onClick={() => setSelectedSlot(slot)}
                
              >
                {slot.displayTime}
              </button>
            ))}
          </div>
        </div>
      )}

      {selectedSlot && (
        <button id ='submit'
          onClick={bookAppointment}
          disabled={loading}
          
        >
          {loading ? 'Booking...' : 'Confirm Booking'}
        </button>
      )}
    </div>
  );
};

export default CalComBooking;
