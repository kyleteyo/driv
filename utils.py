from datetime import datetime, timedelta

def calculate_currency_status(last_mileage_date):
    """Calculate currency status based on last mileage date"""
    if isinstance(last_mileage_date, str):
        last_date = datetime.strptime(last_mileage_date, "%Y-%m-%d")
    else:
        last_date = last_mileage_date
    
    current_date = datetime.now()
    days_since = (current_date - last_date).days
    days_left = 30 - days_since
    
    # Determine status
    if days_since <= 30:
        if days_left <= 5:
            status = "expiring_soon"
        else:
            status = "current"
    else:
        status = "expired"
    
    return {
        'status': status,
        'days_since': days_since,
        'days_left': days_left,
        'last_date': last_date
    }

def format_status_badge(status):
    """Format status badge HTML"""
    if status == "current":
        return """
        <div class="status-current">
            <h3>✅ CURRENT</h3>
            <p>Your mileage currency is up to date.</p>
        </div>
        """
    elif status == "expiring_soon":
        return """
        <div class="status-expiring">
            <h3>⚠️ EXPIRING SOON</h3>
            <p>Your mileage currency expires within 5 days. Please log new mileage soon.</p>
        </div>
        """
    else:  # expired
        return """
        <div class="status-expired">
            <h3>❌ NOT CURRENT</h3>
            <p>Your mileage currency has expired. Please log new mileage immediately.</p>
        </div>
        """

def format_date_display(date_obj):
    """Format date for display"""
    if isinstance(date_obj, str):
        date_obj = datetime.strptime(date_obj, "%Y-%m-%d")
    
    return date_obj.strftime("%B %d, %Y")

def validate_mileage_input(distance):
    """Validate mileage input"""
    try:
        distance_float = float(distance)
        if distance_float <= 0:
            return False, "Distance must be greater than 0"
        if distance_float > 1000:
            return False, "Distance seems unusually high (>1000 KM)"
        return True, ""
    except ValueError:
        return False, "Please enter a valid number"

def get_vehicle_types():
    """Get available vehicle types"""
    return ["Terrex", "Belrex"]

def calculate_summary_stats(user_data):
    """Calculate summary statistics for user data"""
    if user_data.empty:
        return {
            'total_distance': 0,
            'avg_distance': 0,
            'total_entries': 0,
            'terrex_count': 0,
            'belrex_count': 0
        }
    
    return {
        'total_distance': user_data['Distance_KM'].sum(),
        'avg_distance': user_data['Distance_KM'].mean(),
        'total_entries': len(user_data),
        'terrex_count': len(user_data[user_data['Vehicle_Type'] == 'Terrex']),
        'belrex_count': len(user_data[user_data['Vehicle_Type'] == 'Belrex'])
    }
