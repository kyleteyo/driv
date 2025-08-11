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