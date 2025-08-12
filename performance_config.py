# Performance configuration for the application

import streamlit as st
from functools import wraps
import time

def configure_app_performance():
    """Configure Streamlit app for optimal performance"""
    
    # Set page config for performance
    if 'app_configured' not in st.session_state:
        st.set_page_config(
            page_title="MSC Mileage Tracker",
            page_icon="🪖",
            layout="wide",
            initial_sidebar_state="collapsed",
            menu_items={
                'Get Help': None,
                'Report a bug': None,
                'About': "MSC Mileage Tracker - Military Vehicle Management System"
            }
        )
        st.session_state.app_configured = True

# Performance optimization settings - Optimized for speed
CACHE_TTL = 1800  # 30 minutes cache timeout (balanced)
ENABLE_CACHING = True
BATCH_SIZE = 200  # Increased batch size for better performance
MAX_CACHE_SIZE = 200  # Increased cache size for more data
LAZY_LOADING = True  # Enable lazy loading for heavy operations

# Performance optimizations - Balanced cache times for speed vs freshness
CACHE_CONFIG = {
    'user_data_ttl': 900,  # 15 minutes - balanced updates
    'qualifications_ttl': 900,  # 15 minutes - balanced updates  
    'personnel_status_ttl': 600,  # 10 minutes - moderate for team overview
    'tracker_data_ttl': 1800  # 30 minutes - longer for stable data
}

# UI optimizations
UI_CONFIG = {
    'enable_lazy_loading': True,
    'batch_data_operations': True,
    'minimize_api_calls': True,
    'aggressive_caching': True
}

# Global cache for cross-session data sharing
if 'global_data_cache' not in st.session_state:
    st.session_state.global_data_cache = {}

def performance_cache(ttl=CACHE_TTL):
    """Custom caching decorator with aggressive caching"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not ENABLE_CACHING:
                return func(*args, **kwargs)
            
            # Create cache key from function name and args
            cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"
            
            # Initialize cache if needed
            if 'performance_cache' not in st.session_state:
                st.session_state.performance_cache = {}
            
            cache = st.session_state.performance_cache
            
            # Check if we have cached result
            if cache_key in cache:
                cache_data = cache[cache_key]
                if time.time() - cache_data['timestamp'] < ttl:
                    return cache_data['result']
                else:
                    del cache[cache_key]
            
            # Clean cache if too large
            if len(cache) >= MAX_CACHE_SIZE:
                sorted_items = sorted(cache.items(), key=lambda x: x[1]['timestamp'])
                for old_key, _ in sorted_items[:len(cache)//2]:
                    del cache[old_key]
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache[cache_key] = {
                'result': result,
                'timestamp': time.time()
            }
            
            return result
        return wrapper
    return decorator

def get_cached_data(key, ttl=CACHE_TTL):
    """Get data from global cache"""
    cache = st.session_state.global_data_cache
    if key in cache:
        if time.time() - cache[key]['timestamp'] < ttl:
            return cache[key]['data']
        else:
            del cache[key]
    return None

def set_cached_data(key, data):
    """Set data in global cache"""
    cache = st.session_state.global_data_cache
    cache[key] = {
        'data': data,
        'timestamp': time.time()
    }
    
    # Clean cache if too large
    if len(cache) >= MAX_CACHE_SIZE:
        sorted_items = sorted(cache.items(), key=lambda x: x[1]['timestamp'])
        for old_key, _ in sorted_items[:len(cache)//2]:
            del cache[old_key]

def clear_all_caches():
    """Clear all performance caches"""
    if hasattr(st.session_state, 'performance_cache'):
        st.session_state.performance_cache = {}
    if hasattr(st.session_state, 'global_data_cache'):
        st.session_state.global_data_cache = {}
    
    if hasattr(st, 'cache_data'):
        st.cache_data.clear()
    if hasattr(st, 'cache_resource'):
        st.cache_resource.clear()

# High-load configuration for 90+ concurrent users
HIGH_LOAD_CONFIG = {
    'max_concurrent_users': 100,
    'session_timeout': 180,  # 3 minutes
    'cache_ttl': 120,  # 2 minutes for fast updates
    'rate_limit_per_user': 3,  # requests per minute
    'connection_pool_size': 5,  # Reduced Google Sheets connections
    'batch_size': 5,  # Smaller batches for faster processing
    'memory_limit_mb': 512,  # Memory limit per session
}

def configure_high_load_performance():
    """Configure app for 90+ concurrent users"""
    from collections import defaultdict
    import time
    
    # Initialize rate limiting if not exists
    if 'rate_limits' not in st.session_state:
        st.session_state.rate_limits = defaultdict(list)
    
    # Configure reduced cache times for high load
    global CACHE_TTL, MAX_CACHE_SIZE
    CACHE_TTL = HIGH_LOAD_CONFIG['cache_ttl']
    MAX_CACHE_SIZE = 50  # Reduced cache size
    
    # Memory cleanup
    cleanup_session_memory()

def check_rate_limit(user_id):
    """Check if user exceeds rate limit - prevents system overload"""
    import time
    current_time = time.time()
    
    if 'rate_limits' not in st.session_state:
        st.session_state.rate_limits = defaultdict(list)
    
    user_requests = st.session_state.rate_limits[user_id]
    
    # Remove old requests
    user_requests[:] = [req_time for req_time in user_requests 
                       if current_time - req_time < 60]  # 1 minute window
    
    if len(user_requests) >= HIGH_LOAD_CONFIG['rate_limit_per_user']:
        return False
    
    user_requests.append(current_time)
    return True

def cleanup_session_memory():
    """Aggressive memory cleanup for high-load scenarios"""
    import sys
    
    # Clean expired cache entries more aggressively
    if 'performance_cache' in st.session_state:
        cache = st.session_state.performance_cache
        current_time = time.time()
        
        expired_keys = [
            key for key, data in cache.items()
            if current_time - data.get('timestamp', 0) > HIGH_LOAD_CONFIG['cache_ttl']
        ]
        
        for key in expired_keys:
            del cache[key]
    
    # Limit session state size
    session_size = sys.getsizeof(st.session_state)
    if session_size > HIGH_LOAD_CONFIG['memory_limit_mb'] * 1024 * 1024:
        # Clear large data structures
        keys_to_remove = []
        for key, value in st.session_state.items():
            if sys.getsizeof(value) > 100000:  # 100KB
                keys_to_remove.append(key)
        
        for key in keys_to_remove[:5]:  # Remove up to 5 large items
            if key not in ['logged_in', 'username', 'current_page']:
                del st.session_state[key]

def monitor_app_health():
    """Monitor app health and performance"""
    import psutil
    import time
    
    if 'health_check' not in st.session_state:
        st.session_state.health_check = {'last_check': 0, 'alerts': []}
    
    current_time = time.time()
    
    # Check every 30 seconds
    if current_time - st.session_state.health_check['last_check'] > 30:
        try:
            # Check memory usage
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > 85:
                cleanup_session_memory()
                st.session_state.health_check['alerts'].append(
                    f"High memory usage: {memory_percent}% - cleaned cache"
                )
            
            st.session_state.health_check['last_check'] = current_time
        except:
            pass  # psutil might not be available