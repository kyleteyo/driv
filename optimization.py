# App optimization utilities
import streamlit as st
import time
from functools import wraps

# Session-level cache for faster data retrieval
if 'session_cache' not in st.session_state:
    st.session_state.session_cache = {}

def session_cache(ttl=300):
    """Fast session-level caching decorator"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"
            current_time = time.time()
            
            # Check if cached and still valid
            if cache_key in st.session_state.session_cache:
                cached_data = st.session_state.session_cache[cache_key]
                if current_time - cached_data['timestamp'] < ttl:
                    return cached_data['data']
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            st.session_state.session_cache[cache_key] = {
                'data': result,
                'timestamp': current_time
            }
            
            # Clean old cache entries if too many
            if len(st.session_state.session_cache) > 50:
                sorted_items = sorted(
                    st.session_state.session_cache.items(), 
                    key=lambda x: x[1]['timestamp']
                )
                # Keep only newest 25 entries
                st.session_state.session_cache = dict(sorted_items[-25:])
            
            return result
        return wrapper
    return decorator

def clear_session_cache():
    """Clear session cache for fresh data"""
    st.session_state.session_cache = {}

# Lazy loading utility
def lazy_load_data(load_func, placeholder_text="Loading..."):
    """Lazy load data with placeholder"""
    if 'lazy_loaded_data' not in st.session_state:
        st.session_state.lazy_loaded_data = {}
    
    func_name = load_func.__name__
    
    if func_name not in st.session_state.lazy_loaded_data:
        with st.spinner(placeholder_text):
            st.session_state.lazy_loaded_data[func_name] = load_func()
    
    return st.session_state.lazy_loaded_data[func_name]

# Performance monitoring
def performance_timer(func):
    """Decorator to monitor function performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        # Store performance metrics in session state
        if 'performance_metrics' not in st.session_state:
            st.session_state.performance_metrics = {}
        
        st.session_state.performance_metrics[func.__name__] = end_time - start_time
        return result
    return wrapper

# Batch processing utility
def batch_process_data(data_list, batch_size=50):
    """Process data in batches to improve performance"""
    for i in range(0, len(data_list), batch_size):
        yield data_list[i:i + batch_size]

# Memory optimization
def optimize_dataframe(df):
    """Optimize DataFrame memory usage"""
    import pandas as pd
    
    if df.empty:
        return df
    
    # Convert object columns to category where appropriate
    for col in df.select_dtypes(include=['object']).columns:
        if df[col].nunique() / len(df) < 0.5:  # If less than 50% unique values
            df[col] = df[col].astype('category')
    
    # Downcast numeric types
    for col in df.select_dtypes(include=['int64']).columns:
        df[col] = pd.to_numeric(df[col], downcast='integer')
    
    for col in df.select_dtypes(include=['float64']).columns:
        df[col] = pd.to_numeric(df[col], downcast='float')
    
    return df